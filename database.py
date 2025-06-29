"""
Database models for the Blood Test Analyser application.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create a base class for our models
Base = declarative_base()


# Define Analysis model for storing blood test analysis results
class Analysis(Base):
    """Model for storing blood test analysis results"""

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True)
    analysis_id = Column(String(100), unique=True, index=True)
    query = Column(String(500))
    file_analyzed = Column(String(255))
    analysis_result = Column(Text)
    analysis_date = Column(DateTime, default=datetime.now)
    status = Column(
        String(20), default="pending"
    )  # pending, processing, completed, failed

    def __repr__(self):
        return f"<Analysis(id={self.id}, analysis_id={self.analysis_id})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.analysis_id,
            "query": self.query,
            "file_analyzed": self.file_analyzed,
            "analysis_date": self.analysis_date.isoformat(),
            "analysis_result": self.analysis_result,
            "status": self.status,
        }

    # Add property setters to make it easier to update attributes
    @property
    def result(self):
        return self.analysis_result

    @result.setter
    def result(self, value):
        self.analysis_result = value

    @property
    def job_status(self):
        return self.status

    @job_status.setter
    def job_status(self, value):
        self.status = value


# Create engine and session factory
def get_engine(db_url="sqlite:///bloodtest.db"):
    """Get database engine"""
    return create_engine(db_url)


def get_session_factory(engine):
    """Get session factory"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(db_url="sqlite:///bloodtest.db"):
    """Initialize database with tables"""
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return engine
