"""
Loyihani ishga tushirish
========================
Bot va Dashboard ni bir vaqtda ishga tushiradi.
"""

import asyncio
import threading
import logging
from bot import main as bot_main
from dashboard import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def run_dashboard():
    """Flask dashboardni alohida thread'da ishga tushirish"""
    logger.info("🌐 Dashboard ishga tushdi: http://0.0.0.0:5050")
    app.run(host="0.0.0.0", port=5050, debug=False, use_reloader=False)


if __name__ == "__main__":
    # 1. Dashboard'ni alohida thread'da ishga tushirish
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()

    # 2. Bot'ni asosiy thread'da ishga tushirish
    asyncio.run(bot_main())
