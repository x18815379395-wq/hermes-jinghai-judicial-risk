#!/usr/bin/env python3
"""Safe batch client for Jinghai breach-of-trust records.

Credentials are read only from JINGHAI_APP_ID / JINGHAI_API_KEY.
The client never converts request failures into "no records".
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE = "https://www.kqdaas.com"
ENDPOINT = "/DataService/judicial/breach-of-trust/{company}?queryType=1"
RETRY_HTTP = {429, 500, 502, 504}


class JinghaiError(RuntimeError):
    def __init__(self, kind: str, message: str, *, http_status: int | None = None,
                 business_code: Any = None, request_id: str | None = None):
        super().__init__(message)
        self.kind = kind
        self.http_status = http_status
        self.business_code = business_code
        self.request_id = request_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": str(self),
            "http_status": self.http_status,
            "business_code": self.business_code,
            "request_id": self.request_id,
        }


def _credentials() -> tuple[str, str]:
    app_id = os.getenv("JINGHAI_APP_ID", "").strip()
    api_key = os.getenv("JINGHAI_API_KEY", "").strip()
    if not app_id or not api_key:
        raise JinghaiError(
            "missing_credentials",
            "缺少JINGHAI_APP_ID或JINGHAI_API_KEY；未发起计费查询。",
        )
    return app_id, api_key


def _business_code(data: dict[str, Any]) -> Any:
    for key in ("errcode", "status", "code"):
        if key in data and data[key] is not None:
            return data[key]
    return None


def _is_success(data: dict[str, Any]) -> bool:
    code = _business_code(data)
    return code == 200 or data.get("success") is True


def _message(data: dict[str, Any]) -> str:
    return str(data.get("errmsg") or data.get("message") or data.get("msg") or "API请求失败")


def _request_id(headers: Any, data: dict[str, Any]) -> str | None:
    return (headers.get("X-Jinghai-Request-Id") if headers else None) or data.get("requestId") or data.get("request_id")


def call_api(company: str, *, tag: int = 0, page_index: int = 1,
             page_size: int = 20, timeout: float = 15.0,
             max_retries: int = 3, base_url: str | None = None) -> dict[str, Any]:
    company = company.strip()
    if not company:
        raise JinghaiError("invalid_input", "企业名称不能为空。")
    if tag not in (0, 1):
        raise JinghaiError("invalid_input", "tag仅支持0（当前失信）或1（历史失信）。")
    if page_index < 1 or not 1 <= page_size <= 100:
        raise JinghaiError("invalid_input", "page_index须>=1，page_size须为1—100。")
    app_id, api_key = _credentials()
    base = (base_url or os.getenv("JINGHAI_API_BASE") or DEFAULT_BASE).rstrip("/")
    path = ENDPOINT.format(company=urllib.parse.quote(company, safe=""))
    payload = json.dumps({"tag": tag, "pageIndex": page_index, "pageSize": page_size}, ensure_ascii=False).encode("utf-8")
    headers = {
        "X-Jinghai-App-Id": app_id,
        "X-Jinghai-Api-Key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Hermes-Jinghai-Judicial/0.1.0",
    }
    last_error: JinghaiError | None = None
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(base + path, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                http_status = resp.status
                response_headers = resp.headers
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            http_status = exc.code
            response_headers = exc.headers
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                data = {}
            err = JinghaiError(
                "http_error", _message(data) if data else f"HTTP {http_status}",
                http_status=http_status, business_code=_business_code(data),
                request_id=_request_id(response_headers, data),
            )
            if http_status in RETRY_HTTP and attempt < max_retries:
                time.sleep(min(8.0, (2 ** attempt) + random.random() * 0.2))
                last_error = err
                continue
            raise err
        except (urllib.error.URLError, TimeoutError) as exc:
            err = JinghaiError("network_error", f"网络请求失败：{getattr(exc, 'reason', exc)}")
            if attempt < max_retries:
                time.sleep(min(8.0, (2 ** attempt) + random.random() * 0.2))
                last_error = err
                continue
            raise err
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise JinghaiError("invalid_response", "API返回非JSON响应。", http_status=http_status) from exc
        rid = _request_id(response_headers, data)
        if not _is_success(data):
            code = _business_code(data)
            err = JinghaiError("business_error", _message(data), http_status=http_status,
                               business_code=code, request_id=rid)
            if code in RETRY_HTTP and attempt < max_retries:
                time.sleep(min(8.0, (2 ** attempt) + random.random() * 0.2))
                last_error = err
                continue
            raise err
        body = data.get("data")
        if not isinstance(body, dict):
            body = {}
        records = body.get("records")
        if records is None:
            records = body.get("list", [])
        if not isinstance(records, list):
            raise JinghaiError("invalid_response", "成功响应中的records/list不是数组。", request_id=rid)
        total = body.get("total")
        if total is None:
            total = body.get("totalCount", len(records))
        return {
            "company": company,
            "query_status": "success",
            "risk_type": "historical_breach_of_trust" if tag == 1 else "breach_of_trust",
            "page_index": page_index,
            "page_size": page_size,
            "total": total,
            "records": records,
            "request_id": rid,
            "queried_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "source": "Jinghai Data API (third-party clue; verify material hits officially)",
        }
    raise last_error or JinghaiError("unknown", "未知请求错误。")


def batch_query(companies: list[str], **kwargs: Any) -> dict[str, Any]:
    interval = float(kwargs.pop("interval", 0.5))
    seen: set[str] = set()
    clean = []
    for name in companies:
        name = name.strip()
        if name and name not in seen:
            clean.append(name)
            seen.add(name)
    results = []
    for index, company in enumerate(clean):
        try:
            results.append(call_api(company, **kwargs))
        except JinghaiError as exc:
            results.append({"company": company, "query_status": "error", "error": exc.as_dict()})
        if index + 1 < len(clean):
            time.sleep(interval)
    return {
        "summary": {
            "companies": len(clean),
            "success": sum(x.get("query_status") == "success" for x in results),
            "errors": sum(x.get("query_status") == "error" for x in results),
            "with_records": sum(bool(x.get("records")) for x in results),
        },
        "results": results,
    }


def _read_companies(args: argparse.Namespace) -> list[str]:
    values = list(args.company or [])
    if args.input:
        path = Path(args.input)
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                if "company" not in (reader.fieldnames or []):
                    raise JinghaiError("invalid_input", "CSV必须包含company列。")
                values.extend(row.get("company", "") for row in reader)
        else:
            values.extend(path.read_text(encoding="utf-8-sig").splitlines())
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="鲸海数据失信被执行人批量查询（补充线索源）")
    parser.add_argument("--company", action="append", help="企业全称，可重复")
    parser.add_argument("--input", help="UTF-8 TXT（每行一家）或CSV（company列）")
    parser.add_argument("--tag", type=int, choices=[0, 1], default=0, help="0当前失信，1历史失信")
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--output", help="输出JSON文件；省略则打印stdout")
    parser.add_argument("--check", action="store_true", help="只检查配置，不调用API")
    args = parser.parse_args()
    try:
        if args.check:
            _credentials()
            result = {"configured": True, "base_url": os.getenv("JINGHAI_API_BASE", DEFAULT_BASE), "api_key_logged": False}
        else:
            companies = _read_companies(args)
            if not companies:
                raise JinghaiError("invalid_input", "请提供--company或--input。")
            result = batch_query(companies, tag=args.tag, page_index=args.page_index,
                                 page_size=args.page_size, timeout=args.timeout,
                                 max_retries=args.retries, interval=args.interval)
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
            print(json.dumps({"saved": args.output, "summary": result.get("summary")}, ensure_ascii=False))
        else:
            print(rendered)
        return 0
    except JinghaiError as exc:
        print(json.dumps({"ok": False, "error": exc.as_dict()}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
