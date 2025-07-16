import time
import logging
from datetime import datetime
import traceback

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import config
from database import AnalysisTask, AiAnalysisReport, Base, get_session
from stock_analyzer import StockAnalyzer

# --- Configuration ---
SLEEP_INTERVAL = 10  # Seconds to wait between checking for new tasks

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - [Worker] - %(message)s')
logger = logging.getLogger(__name__)


def process_task(task: AnalysisTask, db_session):
    """
    Processes a single analysis task.
    """
    logger.info(f"Starting processing for task ID: {task.id}, stock: {task.stock_code}")
    try:
        # 1. Update task status to 'in_progress'
        task.status = 'in_progress'
        task.updated_at = datetime.now()
        db_session.commit()
        logger.info(f"Task {task.id} status updated to 'in_progress'.")

        # 2. Perform the analysis
        analyzer = StockAnalyzer()
        # Using perform_enhanced_analysis as it returns a structured report
        analysis_result = analyzer.perform_enhanced_analysis(task.stock_code, task.market_type)
        
        logger.info(f"Analysis completed for stock {task.stock_code}. Saving report.")

        # 3. Store the result in AiAnalysisReport table
        now = datetime.now()
        report = AiAnalysisReport(
            stock_code=task.stock_code,
            market_type=task.market_type,
            report_date=now.date(),
            report_hour=now.hour,
            report_content=analysis_result,
            created_at=now
        )
        db_session.add(report)

        # 4. Update task status to 'completed'
        task.status = 'completed'
        task.updated_at = datetime.now()
        db_session.commit()
        logger.info(f"Task {task.id} completed successfully and report saved.")

    except Exception as e:
        logger.error(f"Error processing task {task.id} for stock {task.stock_code}.")
        logger.error(traceback.format_exc())

        # Update task status to 'failed'
        task.status = 'failed'
        task.updated_at = datetime.now()
        db_session.commit()
        logger.warning(f"Task {task.id} status updated to 'failed'.")


def main():
    """
    Main worker loop.
    """
    logger.info("Background worker started. Waiting for tasks...")
    
    while True:
        db_session = None
        try:
            db_session = get_session()

            # Look for a pending task
            pending_task = db_session.query(AnalysisTask)\
                                     .filter(AnalysisTask.status == 'pending')\
                                     .order_by(AnalysisTask.created_at)\
                                     .first()

            if pending_task:
                process_task(pending_task, db_session)
            else:
                # No tasks found, wait for a bit
                time.sleep(SLEEP_INTERVAL)

        except Exception as e:
            logger.error("An unexpected error occurred in the main worker loop.")
            logger.error(traceback.format_exc())
            # Wait longer in case of persistent errors (e.g., DB connection issue)
            time.sleep(SLEEP_INTERVAL * 2)
        finally:
            if db_session:
                db_session.close()


if __name__ == '__main__':
    main() 