import pandas as pd
import akshare as ak
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import logging
from database import init_db, StockInfo, get_session

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_and_store_stocks(session):
    """
    Fetches stock lists from Akshare and stores them in the database.
    """
    fetchers = {
        'A': get_a_share_stocks,
        'HK': get_hk_stocks,
        'US': get_us_stocks
    }

    for market, fetcher in fetchers.items():
        logger.info(f"Fetching stock list for {market} market...")
        try:
            stocks_df = fetcher()
            if stocks_df.empty:
                logger.warning(f"No stocks found for {market} market.")
                continue

            logger.info(f"Found {len(stocks_df)} stocks for {market} market. Storing in database...")
            
            existing_codes = {s.stock_code for s in session.query(StockInfo.stock_code).filter_by(market_type=market).all()}
            
            new_stocks_count = 0
            for _, row in stocks_df.iterrows():
                if row['code'] not in existing_codes:
                    stock_info = StockInfo(
                        stock_code=row['code'],
                        stock_name=row['name'],
                        market_type=market,
                        industry=row.get('industry', None) # Add industry if available
                    )
                    session.add(stock_info)
                    new_stocks_count += 1

            if new_stocks_count > 0:
                session.commit()
                logger.info(f"Successfully stored {new_stocks_count} new stocks for {market} market.")
            else:
                logger.info(f"No new stocks to add for {market} market.")
                session.rollback() # Rollback if no new stocks to prevent holding open transaction

        except Exception as e:
            logger.error(f"Failed to fetch or store stocks for {market} market: {e}")
            session.rollback()

def get_a_share_stocks():
    """Fetches all A-share stock codes and names using a verified function."""
    logger.info("Fetching A-share list...")
    df = ak.stock_zh_a_spot_em()
    df.rename(columns={'代码': 'code', '名称': 'name'}, inplace=True)
    df['industry'] = None
    return df[['code', 'name', 'industry']]

def get_hk_stocks():
    """Fetches all Hong Kong stock codes and names using a verified function."""
    logger.info("Fetching HK stock list...")
    df = ak.stock_hk_spot_em()
    df.rename(columns={'代码': 'code', '名称': 'name'}, inplace=True, errors='ignore')
    df['code'] = df['code'].astype(str).str.zfill(5)
    df['industry'] = None
    return df[['code', 'name', 'industry']]

def get_us_stocks():
    """
    Fetches all US stock codes and names.
    NOTE: akshare does not provide a reliable bulk method to fetch industries for US stocks.
    Industry will be populated as None.
    """
    logger.info("Fetching US stock list (names only)...")
    df = ak.stock_us_spot()
    df.rename(columns={'symbol': 'code','category':'industry'}, inplace=True)
    df['industry'] = None
    return df[['code', 'name', 'industry']]

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()
    
    db_session = get_session()
    
    try:
        logger.info("Starting to seed stock information...")
        fetch_and_store_stocks(db_session)
        logger.info("Stock information seeding process complete.")
    finally:
        db_session.close()
        logger.info("Database session closed.") 