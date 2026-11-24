
import os, time,  json, logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="خدمة التسعير", version="2.0")

SERVICE_KEY = os.environ.get("PRICING_API_KEY", "")

CATALOG = {"A-100": ("سعر الكتالوج 120 دينار", 120),
           "A-200": ("سعر الكتالوج 80 دينار",  80),
           "A-300": ("سعر الكتالوج 45 دينار",  45)}
PROMOS  = {"A-100": ("سعر العرض 95 دينار",      95)}
STATE = Path("state.json")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pricing")

بدأت_الخدمة = time.time()

عدادات = {
    "requests_total": 0,
    "errors_total": 0,
    "latency_ms_sum": 0.0,
    "latency_ms_max": 0.0,
}


@app.middleware("http")
async def قيس_كل_طلب(request: Request, call_next):
    """بتلفّ كل طلب · بتقيس وقته · وبتسجّله."""
    بلّش = time.perf_counter()
    رد = await call_next(request)

    مدة = (time.perf_counter() - بلّش) * 1000
    عدادات["requests_total"] += 1
    عدادات["latency_ms_sum"] += مدة
    if مدة > عدادات["latency_ms_max"]:
        عدادات["latency_ms_max"] = مدة
    if رد.status_code >= 400:
        عدادات["errors_total"] += 1

    مستوى = logging.WARNING if رد.status_code >= 400 else logging.INFO
    log.log(مستوى,
            "path=%s | status=%s | ms=%.1f",
            request.url.path, رد.status_code, مدة)
    return رد


@app.get("/metrics")
def metrics():
    """أرقام خدمتك · للمراقبة."""
    ن = عدادات["requests_total"]
    return {
        "uptime_seconds": round(time.time() - بدأت_الخدمة, 1),
        "requests_total": ن,
        "errors_total":   عدادات["errors_total"],
        "latency_ms_avg": round(عدادات["latency_ms_sum"] / ن, 2) if ن else 0,
        "latency_ms_max": round(عدادات["latency_ms_max"], 2),
    }
def اقرا_العداد() -> int:
    try:
        return int(json.loads(STATE.read_text())["count"])
    except Exception:
        return 0

def زيّد_العداد() -> int:
    n = اقرا_العداد() + 1
    try:
        STATE.write_text(json.dumps({"count": n}))
    except Exception:
        pass
    return n

def سعّر(code: str) -> str:
    نتائج = []
    if code in CATALOG:
        نتائج.append(("catalog",) + CATALOG[code])
    if code in PROMOS:
        نتائج.append(("promo",) + PROMOS[code])
    if not نتائج:
        return ""
    src, txt, price = min(نتائج, key=lambda f: f[2])
    رد = txt
    باقي = [f for f in نتائج if f[0] != src]
    if باقي:
        رد += " · تنبيه: " + " · ".join(t for _, t, _ in باقي)
    return رد
@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>خدمة التسعير</title>
<style>
 body{font-family:system-ui,sans-serif;background:#0f1419;color:#e8eaed;
      display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
 .c{text-align:center;padding:40px}
 h1{font-size:34px;margin:0 0 10px}
 p{color:#9aa0a6;margin:0 0 26px}
 a{display:inline-block;margin:6px;padding:10px 18px;border-radius:8px;
   background:#1f2937;color:#e8eaed;text-decoration:none;font-family:monospace}
 a:hover{background:#2d3748}
</style></head><body><div class="c">
<h1>برعاية عبدالله خدمة التسعير شغّالة ✓</h1>
<p>وهاي على الإنترنت — مش على جهازك</p>
<a href="/quote?code=A-100">/quote?code=A-100</a>
<a href="/health">/health</a>
<a href="/metrics">/metrics</a>
<a href="/docs">/docs</a>
</div></body></html>"""
@app.get("/health")
def health():
    return {"status": "ok",
            "key_loaded": bool(SERVICE_KEY),
            "requests": اقرا_العداد()}
@app.get("/quote")
def quote(code: str):
    رد = سعّر(code)
    if not رد:
        raise HTTPException(status_code=404,
                            detail=f"ما لقيت سعر للكود {code}.")
    زيّد_العداد()
    return {"code": code, "answer": رد}
@app.get("/stats")
def stats():
    return {"count": اقرا_العداد()}
