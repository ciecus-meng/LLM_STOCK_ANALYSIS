import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON, Date, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config

# 读取配置
DATABASE_URL = config.DATABASE_URL or 'sqlite:///data/stock_analyzer.db'
USE_DATABASE = bool(config.DATABASE_URL)

# 创建引擎
engine = create_engine(DATABASE_URL)
Base = declarative_base()


# 定义模型
class StockInfo(Base):
    __tablename__ = 'stock_info'

    id = Column(Integer, primary_key=True)
    stock_code = Column(String(10), nullable=False, index=True)
    stock_name = Column(String(50))
    market_type = Column(String(5))
    industry = Column(String(50))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'market_type': self.market_type,
            'industry': self.industry,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class AnalysisResult(Base):
    __tablename__ = 'analysis_results'

    id = Column(Integer, primary_key=True)
    stock_code = Column(String(10), nullable=False, index=True)
    market_type = Column(String(5))
    analysis_date = Column(DateTime, default=datetime.now)
    score = Column(Float)
    recommendation = Column(String(100))
    technical_data = Column(JSON)
    fundamental_data = Column(JSON)
    capital_flow_data = Column(JSON)
    ai_analysis = Column(Text)

    def to_dict(self):
        return {
            'stock_code': self.stock_code,
            'market_type': self.market_type,
            'analysis_date': self.analysis_date.strftime('%Y-%m-%d %H:%M:%S') if self.analysis_date else None,
            'score': self.score,
            'recommendation': self.recommendation,
            'technical_data': self.technical_data,
            'fundamental_data': self.fundamental_data,
            'capital_flow_data': self.capital_flow_data,
            'ai_analysis': self.ai_analysis
        }


class Portfolio(Base):
    __tablename__ = 'portfolios'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    stocks = Column(JSON)  # 存储股票列表的JSON

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'stocks': self.stocks
        }


class AnalysisTask(Base):
    __tablename__ = 'analysis_tasks'

    id = Column(Integer, primary_key=True)
    stock_code = Column(String(10), nullable=False, index=True)
    market_type = Column(String(5), nullable=False)
    status = Column(String(20), default='pending', index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'market_type': self.market_type,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class AiAnalysisReport(Base):
    __tablename__ = 'ai_analysis_reports'

    id = Column(Integer, primary_key=True)
    stock_code = Column(String(10), nullable=False, index=True)
    market_type = Column(String(5), nullable=False)
    report_date = Column(Date, nullable=False, index=True)
    report_hour = Column(Integer, nullable=False, index=True)
    report_content = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (Index('ix_report_date_hour', 'report_date', 'report_hour'),)

    def to_dict(self):
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'market_type': self.market_type,
            'report_date': self.report_date.strftime('%Y-%m-%d'),
            'report_hour': self.report_hour,
            'report_content': self.report_content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class UserStockNote(Base):
    __tablename__ = 'user_stock_notes'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), default='default_user', index=True)
    stock_code = Column(String(10), nullable=False, index=True)
    market_type = Column(String(5), nullable=False)
    note_date = Column(DateTime, default=datetime.now)
    content = Column(Text)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'stock_code': self.stock_code,
            'market_type': self.market_type,
            'note_date': self.note_date.strftime('%Y-%m-%d %H:%M:%S'),
            'content': self.content
        }


# 创建会话工厂
Session = sessionmaker(bind=engine)


# 初始化数据库
def init_db():
    Base.metadata.create_all(engine, checkfirst=True)


# 获取数据库会话
def get_session():
    return Session()


# 如果启用数据库，则初始化
if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    print("Database initialized.")