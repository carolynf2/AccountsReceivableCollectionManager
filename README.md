# Accounts Receivable Collection Manager

A comprehensive Python-based system for managing accounts receivable collections, tracking payment promises, and optimizing collection efficiency.

## Overview

This system provides a complete solution for managing AR collections with three core capabilities:
- **Collection Prioritization**: Advanced customer prioritization using weighted scoring algorithms
- **Payment Promise Tracking**: Comprehensive promise management with automated follow-up
- **Collection Efficiency Analytics**: Industry-standard metrics and performance reporting

## Features

### Core Components

1. **Database Schema** (`ar_database_schema.sql`)
   - 14-table design covering all aspects of AR collection
   - Customers, invoices, payments, promises, activities, disputes, workflows, and metrics
   - Optimized indexes for performance

2. **Synthetic Data Generator** (`ar_data_generator.py`)
   - Realistic AR collection scenarios for testing
   - 50+ customers with varying payment behaviors
   - Complex invoice patterns and payment histories

3. **Customer Prioritization Engine** (`ar_prioritization.py`)
   - Weighted scoring across 5 dimensions
   - Amount (25%), Aging (30%), Customer history (20%), Relationship value (15%), Collection effort (10%)
   - Automated priority queue generation

4. **Payment Promise Tracker** (`ar_promise_tracker.py`)
   - Complete promise lifecycle management
   - Automated follow-up scheduling
   - Performance reporting and trend analysis

5. **Collection Analytics** (`ar_analytics.py`)
   - Collection Efficiency Index (CEI) calculation
   - Days Sales Outstanding (DSO) tracking
   - Collector performance metrics
   - Comprehensive dashboard system

6. **Workflow Engine** (`ar_workflow_engine.py`)
   - Automated collection workflows based on rules and triggers
   - Configurable escalation paths
   - Integration with all collection activities

7. **Activity Tracker** (`ar_activity_tracker.py`)
   - Complete communication history tracking
   - Follow-up management
   - Activity effectiveness analysis

8. **Aging Analysis** (`ar_aging_analysis.py`)
   - Standard aging bucket analysis (Current, 1-30, 31-60, 61-90, 91-120, 120+)
   - Risk assessment and trend analysis
   - Collection priority recommendations

9. **Main Orchestrator** (`ar_collection_manager.py`)
   - Central coordination system
   - Daily collection process automation
   - Comprehensive reporting

10. **Configuration Management** (`ar_config.py`)
    - Environment-based configuration
    - Validation and backup capabilities
    - Logging configuration

11. **Test Suite** (`test_ar_system.py`)
    - Comprehensive unit and integration tests
    - Performance testing
    - End-to-end workflow validation

## Quick Start

### Installation

1. Ensure Python 3.7+ is installed
2. No external dependencies required - uses only Python standard library
3. Download all files to a single directory

### Basic Usage

```python
from ar_collection_manager import ARCollectionManager

# Initialize the system
manager = ARCollectionManager()

# Initialize with sample data
init_results = manager.initialize_system(generate_sample_data=True)

# Run daily collection process
daily_results = manager.run_daily_collection_process()

# Generate collection dashboard
dashboard = manager.get_collection_dashboard()

# Execute collection actions
action_result = manager.execute_collection_action(
    action_type="phone_call",
    customer_id=1,
    details={
        'contact_person': 'John Smith',
        'duration_minutes': 15,
        'notes': 'Discussed payment arrangement'
    }
)
```

### Command Line Usage

```bash
# Run the main system
python ar_collection_manager.py

# Run tests
python test_ar_system.py

# Generate sample data
python ar_data_generator.py
```

## Configuration

The system uses JSON-based configuration (`ar_config.json`):

```json
{
    "collection_targets": {
        "weekly_calls": 100,
        "weekly_emails": 200,
        "monthly_collection_rate": 85.0
    },
    "risk_thresholds": {
        "high_risk_days": 60,
        "critical_risk_days": 90,
        "large_invoice_threshold": 10000.0
    },
    "workflow_settings": {
        "auto_trigger": true,
        "escalation_enabled": true,
        "legal_referral_threshold": 90
    }
}
```

Environment variables can override configuration:
- `AR_DB_PATH`: Database file path
- `AR_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `AR_ENVIRONMENT`: Environment (development, production)

## Key Metrics

### Collection Efficiency Index (CEI)
```
CEI = (Collections in Period / (Opening AR + Sales in Period - Closing AR)) × 100
```

### Days Sales Outstanding (DSO)
```
DSO = (Accounts Receivable / Average Daily Sales) × Number of Days
```

### Aging Analysis
- **Current**: 0 days past due
- **1-30**: 1-30 days past due
- **31-60**: 31-60 days past due  
- **61-90**: 61-90 days past due
- **91-120**: 91-120 days past due
- **120+**: Over 120 days past due

## Workflow Automation

The system includes default workflows:

1. **Early Reminder** (1-30 days): Email → Phone → Second notice
2. **Standard Collection** (31-60 days): Phone → Letter → Escalation
3. **Intensive Collection** (61-90 days): Supervisor call → Credit hold → Escalation
4. **Legal Referral** (90+ days): Manager review → Legal action

## API Reference

### ARCollectionManager

Main orchestrator class providing centralized management.

#### Methods

- `initialize_system(generate_sample_data=False)`: Initialize complete system
- `run_daily_collection_process()`: Execute daily collection activities
- `get_collection_dashboard()`: Generate comprehensive dashboard
- `execute_collection_action(action_type, customer_id, **kwargs)`: Execute specific collection actions
- `generate_comprehensive_report(report_type)`: Generate detailed reports

### CustomerPrioritizer

Customer prioritization and scoring engine.

#### Methods

- `calculate_customer_priority_score(customer_id)`: Calculate priority score for customer
- `generate_collection_queue(limit=None)`: Generate prioritized collection queue
- `get_high_priority_customers()`: Get customers requiring immediate attention

### PaymentPromiseTracker

Payment promise lifecycle management.

#### Methods

- `create_payment_promise(customer_id, promised_amount, promised_date, **kwargs)`: Create new promise
- `update_promise_status(promise_id, new_status, **kwargs)`: Update promise status
- `process_overdue_promises()`: Process and escalate overdue promises
- `get_promise_performance_report()`: Generate promise performance analytics

### CollectionAnalytics

Collection efficiency and performance analytics.

#### Methods

- `calculate_collection_efficiency_index()`: Calculate CEI metrics
- `calculate_days_sales_outstanding()`: Calculate DSO metrics  
- `analyze_collector_performance()`: Analyze individual collector performance
- `generate_comprehensive_dashboard()`: Generate analytics dashboard

## Database Schema

### Core Tables

- **customers**: Customer master data with credit and collection information
- **invoices**: Invoice records with aging and collection status
- **payments**: Payment records and applications
- **payment_promises**: Promise tracking and fulfillment
- **collection_activities**: Communication and activity history
- **collection_workflows**: Automated workflow definitions
- **disputes**: Dispute management and resolution
- **collection_metrics**: Performance metrics and KPIs

### Relationships

```
customers (1) → (many) invoices
customers (1) → (many) payments  
customers (1) → (many) payment_promises
customers (1) → (many) collection_activities
invoices (1) → (many) payment_applications
invoices (1) → (many) collection_activities
payments (1) → (many) payment_applications
```

## Testing

Run the comprehensive test suite:

```bash
python test_ar_system.py
```

The test suite includes:
- Unit tests for all components
- Integration tests for workflows
- Performance benchmarks
- End-to-end scenario testing

## Performance Considerations

- Database indexes optimized for common queries
- Configurable aging refresh frequency
- Batch processing for large datasets
- Efficient priority queue algorithms
- Caching for frequently accessed data

## Security Features

- No hardcoded credentials
- Configurable database path
- Audit trail for all activities
- Role-based access considerations
- Data validation and sanitization

## Monitoring and Logging

- Comprehensive logging with configurable levels
- Activity tracking and audit trails
- Performance metrics collection
- Error tracking and reporting
- Dashboard monitoring capabilities

## Extensibility

The modular design allows for easy extension:

- Custom scoring algorithms
- Additional workflow actions
- New report types
- Integration with external systems
- Custom analytics and metrics

## Best Practices

1. **Daily Process**: Run daily collection process consistently
2. **Priority Management**: Focus on high-priority customers first
3. **Promise Tracking**: Monitor promise fulfillment closely
4. **Activity Documentation**: Record all customer interactions
5. **Regular Analysis**: Review metrics and trends regularly
6. **Configuration Management**: Keep configuration current
7. **Testing**: Test changes thoroughly
8. **Backup**: Regular database backups

## Troubleshooting

### Common Issues

1. **Database Lock**: Ensure only one process accesses database at a time
2. **Missing Data**: Run data generator if starting fresh
3. **Configuration Errors**: Validate configuration with built-in validator
4. **Performance Issues**: Check database indexes and aging frequency
5. **Memory Usage**: Monitor for large result sets

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check system status:
```python
manager = ARCollectionManager()
dashboard = manager.get_collection_dashboard()
print(dashboard['key_metrics'])
```

## Support and Contributing

This is a comprehensive demonstration system. For production use:

1. Add proper error handling
2. Implement authentication and authorization
3. Add data validation
4. Integrate with existing systems
5. Add backup and recovery procedures
6. Implement monitoring and alerting
7. Add API endpoints for external access
8. Enhance reporting capabilities

## License

This code is provided as an educational example and demonstration of AR collection management concepts.

## Version History

- **1.0.0**: Initial release with all core components
  - Complete database schema
  - All 11 major components implemented
  - Comprehensive test suite
  - Configuration management
  - Documentation and examples