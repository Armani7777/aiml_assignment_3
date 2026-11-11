"""Скриншоты интерфейса ResearchAssist для презентации (Playwright + Edge)."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8501"
TOPIC = ("This research addresses subsurface imaging with radar using deep learning. The problem is to classify "
         "materials and estimate terrain and subsurface parameters from radar sounder and ground penetrating radar "
         "signals, which are noisy and hard to interpret manually. We propose a neural network that learns radar "
         "signal features and solves the geophysical inverse problem, using seismic-style full waveform inversion "
         "and denoising. We evaluate classification accuracy, inversion error and robustness to noise on simulated "
         "and real radar measurements.")


def nav(page, name):
    page.get_by_role("link", name=name).first.click()
    page.wait_for_timeout(2500)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    page = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    page.goto(URL); page.wait_for_selector("text=1. Исходный документ", timeout=60000); page.wait_for_timeout(1500)
    page.get_by_text("Ввести тему", exact=True).click(); page.wait_for_timeout(800)
    page.locator("textarea").fill(TOPIC); page.keyboard.press("Tab"); page.wait_for_timeout(800)
    page.screenshot(path=str(OUT / "launch.png"))
    page.get_by_role("button", name="🚀 Запустить").click()
    page.wait_for_function("document.querySelectorAll('.ra-msg').length >= 7", timeout=60000)
    page.screenshot(path=str(OUT / "live.png"))
    page.locator(".ra-card:has(svg)").first.screenshot(path=str(OUT / "el_diagram.png"))
    page.wait_for_selector("text=Готово! Откройте", timeout=60000); page.wait_for_timeout(1000)
    page.screenshot(path=str(OUT / "live_done.png"))
    page.locator(".ra-card:has(.ra-msg)").first.screenshot(path=str(OUT / "el_feed.png"))
    nav(page, "Результаты")
    page.screenshot(path=str(OUT / "results_top.png"))
    page.get_by_role("tab", name="✍️ Related Work").scroll_into_view_if_needed(); page.mouse.wheel(0, 520)
    page.wait_for_timeout(1200); page.screenshot(path=str(OUT / "results_draft.png"))
    page.locator(".ra-draft").first.screenshot(path=str(OUT / "el_draft.png"))
    page.get_by_role("tab", name="📚 Найденные статьи").click(); page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / "results_papers.png"))
    page.locator('[data-testid="stDataFrame"]').first.screenshot(path=str(OUT / "el_papers.png"))
    page.get_by_role("tab", name="🧩 Темы и пробелы").click(); page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / "results_themes.png"))
    nav(page, "Журнал"); page.screenshot(path=str(OUT / "journal.png"))
    # ошибка входа
    nav(page, "Запуск")
    page.get_by_text("Пример из набора", exact=True).click(); page.wait_for_timeout(800)
    page.locator('[data-testid="stSelectbox"]').first.click(); page.wait_for_timeout(800)
    page.get_by_role("option", name="Неподдерживаемый формат (CSV)").click(); page.wait_for_timeout(800)
    page.get_by_role("button", name="🚀 Запустить").click()
    page.wait_for_selector("text=Как исправить", timeout=30000); page.wait_for_timeout(1000)
    page.locator(".ra-err").first.scroll_into_view_if_needed(); page.wait_for_timeout(600)
    page.screenshot(path=str(OUT / "error.png"))
    page.locator(".ra-err").first.screenshot(path=str(OUT / "el_error.png"))
    nav(page, "Эксперименты"); page.screenshot(path=str(OUT / "experiments.png"))
    page.locator('[data-testid="stDataFrame"]').first.screenshot(path=str(OUT / "el_scenarios.png"))
    b.close()
print("ok", sorted(x.name for x in OUT.iterdir()))
