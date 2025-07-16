import time
import logging
from datetime import datetime
import traceback

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import config
from database import AnalysisTask, AiAnalysisReport, Base, get_session, init_db
from stock_analyzer import StockAnalyzer

# --- Configuration ---
SLEEP_INTERVAL = 10  # Seconds to wait between checking for new tasks

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - [Worker] - %(message)s')
logger = logging.getLogger(__name__)


def process_task(task: AnalysisTask, db_session):
    """
    Processes a single analysis task based on its type.
    """
    logger.info(f"Picked up task {task.id} with type '{task.task_type}'.")

    try:
        if task.task_type == 'single_stock':
            process_single_stock_task(task, db_session)
        elif task.task_type == 'market_scan':
            process_market_scan_task(task, db_session)
        else:
            # For other task types, we currently don't have a specific processor.
            # We will log it and mark as complete to avoid retries.
            logger.warning(f"No specific processor for task type '{task.task_type}'. Marking as completed.")
            task.status = 'completed' # Or 'failed' with an appropriate error message
            task.error = f"Unsupported task type: {task.task_type}"
            task.updated_at = datetime.now()
            db_session.commit()

    except Exception as e:
        logger.error(f"Unhandled error while processing task {task.id}: {e}")
        logger.error(traceback.format_exc())
        task.status = 'failed'
        task.error = str(e)
        task.updated_at = datetime.now()
        db_session.commit()


def process_market_scan_task(task: AnalysisTask, db_session):
    """
    Processes a market scan task.
    """
    params = task.parameters
    stock_list = params.get('stock_list', [])
    min_score = params.get('min_score', 60)
    market_type = params.get('market_type', 'A')

    logger.info(f"Starting market scan task {task.id} for {len(stock_list)} stocks.")
    
    try:
        task.status = 'in_progress'
        task.total = len(stock_list)
        task.progress = 0
        db_session.commit()

        analyzer = StockAnalyzer()
        qualified_stocks = []
        
        for i, stock_code in enumerate(stock_list):
            logger.info(f"Scanning {stock_code} ({i+1}/{len(stock_list)}) for task {task.id}")
            try:
                # Use quick analysis which doesn't involve AI
                result = analyzer.quick_analyze_stock(stock_code, market_type)
                
                if result and not result.get('error') and result.get('score', 0) >= min_score:
                    qualified_stocks.append(result)
            except Exception as e:
                logger.error(f"Error analyzing stock {stock_code} in task {task.id}: {e}")
            
            # Update progress in the database
            task.progress = i + 1
            db_session.commit()

        # Sort final results by score
        qualified_stocks.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        task.result = {'qualified_stocks': qualified_stocks}
        task.status = 'completed'
        task.updated_at = datetime.now()
        db_session.commit()
        logger.info(f"Market scan task {task.id} completed. Found {len(qualified_stocks)} qualified stocks.")

    except Exception as e:
        logger.error(f"Critical error processing market scan task {task.id}: {e}")
        logger.error(traceback.format_exc())
        task.status = 'failed'
        task.error = traceback.format_exc()
        task.updated_at = datetime.now()
        db_session.commit()


def process_single_stock_task(task: AnalysisTask, db_session):
    """
    Processes a single stock analysis task.
    """
    params = task.parameters
    stock_code = params.get('stock_code')
    market_type = params.get('market_type')

    if not stock_code or not market_type:
        logger.error(f"Task {task.id} is missing 'stock_code' or 'market_type' in parameters.")
        task.status = 'failed'
        task.error = "Missing 'stock_code' or 'market_type' in parameters."
        task.updated_at = datetime.now()
        db_session.commit()
        return

    logger.info(f"Starting processing for task ID: {task.id}, stock: {stock_code}")
    try:
        # 1. Update task status to 'in_progress'
        task.status = 'in_progress'
        task.updated_at = datetime.now()
        db_session.commit()
        logger.info(f"Task {task.id} status updated to 'in_progress'.")

        # 2. Perform the analysis
        analyzer = StockAnalyzer()
        analysis_result = analyzer.perform_enhanced_analysis(stock_code, market_type)
        
        logger.info(f"Analysis completed for stock {stock_code}. Saving report.")

        # 3. Store the result in AiAnalysisReport table
        now = datetime.now()
        report = AiAnalysisReport(
            stock_code=stock_code,
            market_type=market_type,
            report_date=now.date(),
            report_hour=now.hour,
            report_content=analysis_result,
            created_at=now
        )
        db_session.add(report)

        # 4. Update task status to 'completed'
        task.status = 'completed'
        task.result = analysis_result
        task.updated_at = datetime.now()
        db_session.commit()
        logger.info(f"Task {task.id} completed successfully and report saved.")

    except Exception as e:
        logger.error(f"Error processing task {task.id} for stock {stock_code}.")
        logger.error(traceback.format_exc())

        # Update task status to 'failed'
        task.status = 'failed'
        task.error = traceback.format_exc()
        task.updated_at = datetime.now()
        db_session.commit()
        logger.warning(f"Task {task.id} status updated to 'failed'.")


def main():
    """
    Main worker loop.
    """
    logger.info("Initializing database for worker...")
    init_db()
    logger.info("Database initialized.")
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