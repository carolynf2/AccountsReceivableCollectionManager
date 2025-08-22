"""
AR Collection Manager Configuration Management
Centralized configuration management with environment-based settings and validation
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class CollectionTargets:
    weekly_calls: int = 100
    weekly_emails: int = 200
    monthly_collection_rate: float = 85.0
    daily_activities_per_collector: int = 20
    promise_follow_up_days: int = 3

@dataclass
class RiskThresholds:
    high_risk_days: int = 60
    critical_risk_days: int = 90
    large_invoice_threshold: float = 10000.0
    concentration_risk_percentage: float = 20.0
    payment_reliability_threshold: int = 40

@dataclass
class WorkflowSettings:
    auto_trigger: bool = True
    escalation_enabled: bool = True
    legal_referral_threshold: int = 90
    credit_hold_threshold: int = 60
    max_retry_attempts: int = 3
    escalation_delay_days: int = 7

@dataclass
class DatabaseSettings:
    db_path: str = "ar_collection.db"
    backup_enabled: bool = True
    backup_frequency: str = "daily"
    backup_retention_days: int = 30
    vacuum_frequency: str = "weekly"

@dataclass
class LoggingSettings:
    log_level: str = "INFO"
    log_file: str = "ar_collection.log"
    max_file_size_mb: int = 50
    backup_count: int = 5
    console_output: bool = True
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

@dataclass
class NotificationSettings:
    email_enabled: bool = False
    email_recipients: list = None
    critical_alerts_enabled: bool = True
    daily_summary_enabled: bool = True
    webhook_url: Optional[str] = None

@dataclass
class ARCollectionConfig:
    collection_targets: CollectionTargets = None
    risk_thresholds: RiskThresholds = None
    workflow_settings: WorkflowSettings = None
    database_settings: DatabaseSettings = None
    logging_settings: LoggingSettings = None
    notification_settings: NotificationSettings = None
    auto_workflow_execution: bool = True
    daily_priority_refresh: bool = True
    promise_follow_up_enabled: bool = True
    aging_refresh_frequency: str = "daily"
    environment: str = "production"
    
    def __post_init__(self):
        if self.collection_targets is None:
            self.collection_targets = CollectionTargets()
        if self.risk_thresholds is None:
            self.risk_thresholds = RiskThresholds()
        if self.workflow_settings is None:
            self.workflow_settings = WorkflowSettings()
        if self.database_settings is None:
            self.database_settings = DatabaseSettings()
        if self.logging_settings is None:
            self.logging_settings = LoggingSettings()
        if self.notification_settings is None:
            self.notification_settings = NotificationSettings(email_recipients=[])

class ConfigManager:
    def __init__(self, config_file: str = "ar_config.json"):
        self.config_file = config_file
        self.config: ARCollectionConfig = None
        self.logger = logging.getLogger(__name__)
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file or create default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                self.config = self._dict_to_config(config_data)
                self.logger.info(f"Configuration loaded from {self.config_file}")
            else:
                # Create default configuration
                self.config = ARCollectionConfig()
                self.save_config()
                self.logger.info(f"Default configuration created and saved to {self.config_file}")
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.config = ARCollectionConfig()

    def _dict_to_config(self, config_dict: Dict[str, Any]) -> ARCollectionConfig:
        """Convert dictionary to configuration object"""
        # Extract nested dictionaries and convert to dataclasses
        collection_targets = CollectionTargets(**config_dict.get('collection_targets', {}))
        risk_thresholds = RiskThresholds(**config_dict.get('risk_thresholds', {}))
        workflow_settings = WorkflowSettings(**config_dict.get('workflow_settings', {}))
        database_settings = DatabaseSettings(**config_dict.get('database_settings', {}))
        logging_settings = LoggingSettings(**config_dict.get('logging_settings', {}))
        notification_settings = NotificationSettings(**config_dict.get('notification_settings', {}))
        
        # Create main config object
        config = ARCollectionConfig(
            collection_targets=collection_targets,
            risk_thresholds=risk_thresholds,
            workflow_settings=workflow_settings,
            database_settings=database_settings,
            logging_settings=logging_settings,
            notification_settings=notification_settings,
            auto_workflow_execution=config_dict.get('auto_workflow_execution', True),
            daily_priority_refresh=config_dict.get('daily_priority_refresh', True),
            promise_follow_up_enabled=config_dict.get('promise_follow_up_enabled', True),
            aging_refresh_frequency=config_dict.get('aging_refresh_frequency', 'daily'),
            environment=config_dict.get('environment', 'production')
        )
        
        return config

    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            config_dict = self._config_to_dict()
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=4, default=str)
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False

    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert configuration object to dictionary"""
        return {
            'collection_targets': asdict(self.config.collection_targets),
            'risk_thresholds': asdict(self.config.risk_thresholds),
            'workflow_settings': asdict(self.config.workflow_settings),
            'database_settings': asdict(self.config.database_settings),
            'logging_settings': asdict(self.config.logging_settings),
            'notification_settings': asdict(self.config.notification_settings),
            'auto_workflow_execution': self.config.auto_workflow_execution,
            'daily_priority_refresh': self.config.daily_priority_refresh,
            'promise_follow_up_enabled': self.config.promise_follow_up_enabled,
            'aging_refresh_frequency': self.config.aging_refresh_frequency,
            'environment': self.config.environment,
            'last_updated': datetime.now().isoformat()
        }

    def get_config(self) -> ARCollectionConfig:
        """Get current configuration"""
        return self.config

    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with new values"""
        try:
            # Convert current config to dict
            current_dict = self._config_to_dict()
            
            # Apply updates
            self._deep_update(current_dict, updates)
            
            # Convert back to config object
            self.config = self._dict_to_config(current_dict)
            
            # Save updated configuration
            return self.save_config()
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False

    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """Recursively update nested dictionaries"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration settings"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate collection targets
        if self.config.collection_targets.weekly_calls <= 0:
            validation_results['errors'].append("Weekly calls target must be positive")
            validation_results['valid'] = False
        
        if self.config.collection_targets.monthly_collection_rate < 0 or self.config.collection_targets.monthly_collection_rate > 100:
            validation_results['errors'].append("Monthly collection rate must be between 0 and 100")
            validation_results['valid'] = False
        
        # Validate risk thresholds
        if self.config.risk_thresholds.high_risk_days >= self.config.risk_thresholds.critical_risk_days:
            validation_results['errors'].append("High risk days must be less than critical risk days")
            validation_results['valid'] = False
        
        if self.config.risk_thresholds.large_invoice_threshold <= 0:
            validation_results['errors'].append("Large invoice threshold must be positive")
            validation_results['valid'] = False
        
        # Validate workflow settings
        if self.config.workflow_settings.legal_referral_threshold <= self.config.workflow_settings.credit_hold_threshold:
            validation_results['warnings'].append("Legal referral threshold should typically be higher than credit hold threshold")
        
        # Validate database settings
        db_path = self.config.database_settings.db_path
        if not db_path or not db_path.endswith('.db'):
            validation_results['errors'].append("Database path must end with .db extension")
            validation_results['valid'] = False
        
        # Validate logging settings
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.config.logging_settings.log_level not in valid_log_levels:
            validation_results['errors'].append(f"Log level must be one of: {valid_log_levels}")
            validation_results['valid'] = False
        
        # Validate aging refresh frequency
        valid_frequencies = ['hourly', 'daily', 'weekly']
        if self.config.aging_refresh_frequency not in valid_frequencies:
            validation_results['errors'].append(f"Aging refresh frequency must be one of: {valid_frequencies}")
            validation_results['valid'] = False
        
        return validation_results

    def get_environment_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables"""
        overrides = {}
        
        # Database settings
        if os.getenv('AR_DB_PATH'):
            overrides.setdefault('database_settings', {})['db_path'] = os.getenv('AR_DB_PATH')
        
        # Logging settings
        if os.getenv('AR_LOG_LEVEL'):
            overrides.setdefault('logging_settings', {})['log_level'] = os.getenv('AR_LOG_LEVEL')
        
        if os.getenv('AR_LOG_FILE'):
            overrides.setdefault('logging_settings', {})['log_file'] = os.getenv('AR_LOG_FILE')
        
        # Environment
        if os.getenv('AR_ENVIRONMENT'):
            overrides['environment'] = os.getenv('AR_ENVIRONMENT')
        
        # Workflow settings
        if os.getenv('AR_AUTO_WORKFLOW') is not None:
            overrides['auto_workflow_execution'] = os.getenv('AR_AUTO_WORKFLOW').lower() == 'true'
        
        # Collection targets
        if os.getenv('AR_WEEKLY_CALLS'):
            overrides.setdefault('collection_targets', {})['weekly_calls'] = int(os.getenv('AR_WEEKLY_CALLS'))
        
        if os.getenv('AR_COLLECTION_RATE'):
            overrides.setdefault('collection_targets', {})['monthly_collection_rate'] = float(os.getenv('AR_COLLECTION_RATE'))
        
        return overrides

    def apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration"""
        overrides = self.get_environment_overrides()
        if overrides:
            self.update_config(overrides)
            self.logger.info(f"Applied {len(overrides)} environment overrides")

    def backup_config(self, backup_path: Optional[str] = None) -> bool:
        """Create a backup of current configuration"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"{self.config_file}.backup_{timestamp}"
            
            config_dict = self._config_to_dict()
            with open(backup_path, 'w') as f:
                json.dump(config_dict, f, indent=4, default=str)
            
            self.logger.info(f"Configuration backed up to {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup configuration: {e}")
            return False

    def restore_config(self, backup_path: str) -> bool:
        """Restore configuration from backup"""
        try:
            if not os.path.exists(backup_path):
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            with open(backup_path, 'r') as f:
                config_data = json.load(f)
            
            self.config = self._dict_to_config(config_data)
            self.save_config()
            
            self.logger.info(f"Configuration restored from {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore configuration: {e}")
            return False

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            'environment': self.config.environment,
            'database_path': self.config.database_settings.db_path,
            'log_level': self.config.logging_settings.log_level,
            'auto_workflow_execution': self.config.auto_workflow_execution,
            'weekly_call_target': self.config.collection_targets.weekly_calls,
            'collection_rate_target': self.config.collection_targets.monthly_collection_rate,
            'high_risk_threshold': self.config.risk_thresholds.high_risk_days,
            'legal_referral_threshold': self.config.workflow_settings.legal_referral_threshold,
            'config_file': self.config_file,
            'last_validation': self.validate_config()['valid']
        }

# Logging configuration setup
def setup_logging(config: ARCollectionConfig) -> None:
    """Setup logging based on configuration"""
    log_settings = config.logging_settings
    
    # Create formatters
    formatter = logging.Formatter(log_settings.log_format)
    
    # Setup file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_settings.log_file,
        maxBytes=log_settings.max_file_size_mb * 1024 * 1024,
        backupCount=log_settings.backup_count
    )
    file_handler.setFormatter(formatter)
    
    # Setup console handler if enabled
    handlers = [file_handler]
    if log_settings.console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_settings.log_level),
        handlers=handlers,
        force=True
    )

# Usage example and testing
if __name__ == "__main__":
    import logging.handlers
    
    # Initialize configuration manager
    config_manager = ConfigManager("ar_config_test.json")
    
    # Get current configuration
    config = config_manager.get_config()
    print(f"Current environment: {config.environment}")
    print(f"Weekly calls target: {config.collection_targets.weekly_calls}")
    
    # Validate configuration
    validation = config_manager.validate_config()
    print(f"Configuration valid: {validation['valid']}")
    if validation['errors']:
        print(f"Errors: {validation['errors']}")
    if validation['warnings']:
        print(f"Warnings: {validation['warnings']}")
    
    # Update configuration
    updates = {
        'collection_targets': {
            'weekly_calls': 150
        },
        'environment': 'development'
    }
    
    success = config_manager.update_config(updates)
    print(f"Configuration updated: {success}")
    
    # Apply environment overrides
    config_manager.apply_environment_overrides()
    
    # Get configuration summary
    summary = config_manager.get_config_summary()
    print(f"Configuration summary: {summary}")
    
    # Setup logging
    setup_logging(config_manager.get_config())
    
    # Test logging
    logger = logging.getLogger("test")
    logger.info("Configuration management test completed successfully")
    
    # Cleanup test file
    if os.path.exists("ar_config_test.json"):
        os.remove("ar_config_test.json")