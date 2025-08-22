# Accounts Receivable Collection Manager

A comprehensive Python-based system for managing accounts receivable collections with automated prioritization, payment tracking, and efficiency analysis.

## Features

### 🎯 **Smart Collection Prioritization**
- **Multi-factor Priority Scoring**: Considers days overdue, amount owed, customer risk rating, broken promises, and last contact date
- **Risk Categorization**: Automatically categorizes customers into Critical, High, Medium, and Low priority groups
- **Customizable Weights**: Adjust priority calculation weights based on your collection strategy
- **Collection Recommendations**: AI-generated specific recommendations for each customer

### 📊 **Payment & Promise Tracking**
- **Payment Processing**: Record and track all customer payments with detailed transaction history
- **Promise Management**: Track payment promises, monitor compliance, and identify broken commitments
- **Automated Balance Updates**: Invoice balances automatically adjust when payments are recorded
- **Payment Method Tracking**: Support for various payment methods (Check, Wire, ACH, Credit Card, etc.)

### 📈 **Collection Efficiency Analytics**
- **Collection Rate**: Calculate percentage of receivables collected over time periods
- **Days Sales Outstanding (DSO)**: Monitor how quickly you collect receivables
- **Promise Keeping Rate**: Track customer reliability in keeping payment commitments
- **Contact Success Rate**: Measure effectiveness of collection activities
- **Aging Reports**: Detailed breakdown of receivables by age categories

### 💼 **Customer & Invoice Management**
- **Customer Profiles**: Comprehensive customer information with risk ratings and credit limits
- **Invoice Tracking**: Full invoice lifecycle management with automated status updates
- **Activity Logging**: Detailed collection activity tracking with outcomes and follow-up dates
- **Contact History**: Complete timeline of all customer interactions

### 📋 **Professional Reporting**
- **Priority Lists**: Ranked customer lists based on collection urgency
- **Dashboard View**: Executive summary with key metrics and alerts
- **Aging Analysis**: Standard 30/60/90 day aging reports
- **Efficiency Reports**: Detailed collection performance analytics
- **Export Capabilities**: Generate reports for management and analysis

## Installation

### Requirements
- Python 3.7 or higher
- SQLite (included with Python)
- No external dependencies required

### Setup
1. Clone or download the project files
2. Navigate to the project directory
3. Run the application:

```bash
python main.py
```

## Quick Start

### 1. Load Sample Data
```bash
python main.py --sample-data
```

### 2. View Dashboard
```bash
python main.py --dashboard
```

### 3. See Priority List
```bash
python main.py --priority-list
```

### 4. Interactive Mode
```bash
python main.py
```

## Database Schema

The system uses SQLite with the following core tables:

- **customers**: Customer information, risk ratings, contact details
- **invoices**: Invoice records with amounts, due dates, and statuses
- **payments**: Payment transactions and methods
- **collection_activities**: Collection efforts and outcomes
- **payment_promises**: Payment commitments and tracking
- **collection_metrics**: Historical efficiency measurements

## Usage Guide

### Customer Management
```python
# Add a new customer
customer_data = {
    'customer_name': 'ABC Company',
    'email': 'billing@abc.com',
    'credit_limit': 25000,
    'risk_rating': 'MEDIUM'
}
customer_id = customer_manager.add_customer(customer_data)
```

### Invoice Management
```python
# Create an invoice
invoice_data = {
    'customer_id': 1,
    'invoice_number': 'INV-001',
    'invoice_date': date(2024, 1, 15),
    'due_date': date(2024, 2, 14),
    'amount': 5000.00
}
invoice_id = invoice_manager.add_invoice(invoice_data)
```

### Payment Processing
```python
# Record a payment
payment_data = {
    'invoice_id': 1,
    'payment_date': date.today(),
    'amount': 2500.00,
    'payment_method': 'CHECK',
    'reference_number': 'CHK-12345'
}
payment_id = payment_manager.add_payment(payment_data)
```

### Collection Activities
```python
# Log collection activity
activity_data = {
    'customer_id': 1,
    'activity_type': 'CALL',
    'outcome': 'PROMISE_TO_PAY',
    'notes': 'Customer promised payment by Friday',
    'follow_up_date': date.today() + timedelta(days=3)
}
activity_id = activity_manager.add_activity(activity_data)
```

### Priority Calculation
```python
# Get prioritized customer list
prioritizer = CollectionPrioritizer(db_manager)
priority_list = prioritizer.get_prioritized_collection_list(limit=20)

# Get collection recommendations
recommendations = prioritizer.get_collection_recommendations(customer_id)
```

### Efficiency Analysis
```python
# Generate efficiency report
calculator = CollectionEfficiencyCalculator(db_manager)
report = calculator.generate_efficiency_report(start_date, end_date)

print(f"Collection Rate: {report['collection_rate']:.1f}%")
print(f"DSO: {report['days_sales_outstanding']:.1f} days")
```

## Priority Scoring Algorithm

The system calculates priority scores based on five weighted factors:

1. **Days Overdue** (Weight: 2.0)
   - 2 points per day overdue
   - Capped at 100 points maximum

2. **Outstanding Amount** (Weight: 1.5)
   - Logarithmic scale: log10(amount) × 10
   - Gives appropriate weight to large balances

3. **Risk Rating** (Weight: 1.8)
   - LOW: 10 points
   - MEDIUM: 50 points  
   - HIGH: 100 points

4. **Broken Promises** (Weight: 2.5)
   - 20 points per broken promise
   - Heavily penalizes unreliable customers

5. **Last Contact Date** (Weight: 1.2)
   - 2 points per day since last contact
   - Encourages regular customer communication

**Final Score = Σ(Factor Score × Weight)**

## Collection Recommendations

The system provides specific, actionable recommendations:

- **CRITICAL** (Score > 500): Legal proceedings consideration
- **HIGH PRIORITY** (Score 300-500): Daily contact attempts
- **MEDIUM PRIORITY** (Score 150-300): Contact within 3-5 days
- **LOW PRIORITY** (Score < 150): Standard collection process

Additional context-specific recommendations cover:
- Aging-based escalations
- Risk-based credit decisions
- Contact frequency adjustments
- Amount-based executive involvement

## Efficiency Metrics

### Collection Rate
Percentage of receivables collected over a time period:
```
Collection Rate = (Collections in Period / Starting Receivables) × 100
```

### Days Sales Outstanding (DSO)
Average number of days to collect receivables:
```
DSO = Current Receivables / (Sales in Last 90 Days / 90)
```

### Promise Keeping Rate
Reliability of customer payment commitments:
```
Promise Rate = (Promises Kept / Total Promises) × 100
```

### Contact Success Rate
Effectiveness of collection activities:
```
Success Rate = (Successful Contacts / Total Activities) × 100
```

## File Structure

```
ar-collection-manager/
├── main.py                     # Main application interface
├── database.py                 # Database management classes
├── database_schema.sql         # Database schema definition
├── collection_prioritizer.py   # Priority and efficiency algorithms
├── test_system.py             # System testing script
├── requirements.txt           # Python dependencies
├── README.md                  # This documentation
└── ar_collection.db           # SQLite database (created on first run)
```

## API Reference

### DatabaseManager
- `execute_query(query, params)`: Execute SELECT queries
- `execute_update(query, params)`: Execute INSERT/UPDATE/DELETE
- `execute_insert(query, params)`: Execute INSERT and return ID

### CustomerManager
- `add_customer(customer_data)`: Add new customer
- `get_customer(customer_id)`: Retrieve customer by ID
- `get_customer_summary()`: Get all customers with balances
- `update_customer(customer_id, data)`: Update customer info

### InvoiceManager
- `add_invoice(invoice_data)`: Create new invoice
- `get_overdue_invoices()`: Get all overdue invoices
- `get_aging_report()`: Generate aging analysis
- `update_invoice_balance(invoice_id, balance)`: Update balance

### PaymentManager
- `add_payment(payment_data)`: Record new payment
- `get_invoice_payments(invoice_id)`: Get payments for invoice
- `get_customer_payments(customer_id)`: Get customer payments

### CollectionActivityManager
- `add_activity(activity_data)`: Log collection activity
- `get_customer_activities(customer_id)`: Get customer activities
- `get_follow_up_activities(date)`: Get scheduled follow-ups

### PaymentPromiseManager
- `add_promise(promise_data)`: Record payment promise
- `update_promise_status(promise_id, status)`: Update promise
- `get_pending_promises()`: Get active promises
- `get_overdue_promises()`: Get broken promises

### CollectionPrioritizer
- `get_prioritized_collection_list(limit)`: Get ranked customers
- `get_collection_recommendations(customer_id)`: Get recommendations
- `get_customers_by_risk_category()`: Categorize by risk
- `calculate_priority_score(customer_data)`: Calculate score

### CollectionEfficiencyCalculator
- `calculate_collection_rate(start, end)`: Calculate collection %
- `calculate_dso()`: Calculate days sales outstanding
- `calculate_promise_keeping_rate(start, end)`: Promise reliability
- `generate_efficiency_report(start, end)`: Full report

## Best Practices

### Collection Strategy
1. **Focus on High Priority**: Use the priority scoring to focus efforts
2. **Regular Contact**: Maintain consistent customer communication
3. **Promise Tracking**: Monitor and follow up on payment commitments
4. **Risk Management**: Adjust credit terms based on risk ratings
5. **Efficiency Monitoring**: Track and improve collection metrics

### Data Management
1. **Regular Backups**: Backup the SQLite database file regularly
2. **Activity Logging**: Record all customer interactions consistently
3. **Accurate Data**: Maintain current customer contact information
4. **Timely Updates**: Record payments and activities promptly
5. **Historical Analysis**: Use metrics to identify trends and opportunities

### System Maintenance
1. **Database Optimization**: SQLite handles optimization automatically
2. **Regular Reports**: Generate monthly efficiency reports
3. **Weight Tuning**: Adjust priority weights based on results
4. **User Training**: Ensure all users understand the priority system
5. **Process Documentation**: Document your specific collection procedures

## Troubleshooting

### Common Issues

**Database Errors**
- Ensure the application has write permissions in the directory
- Check that the database file isn't locked by another process

**Priority Scores**
- Verify customer data is complete and accurate
- Check that priority weights are set appropriately
- Ensure invoice due dates are correct

**Efficiency Metrics**
- Confirm payment dates are recorded accurately
- Verify that collection activities are logged consistently
- Check that the date ranges for reports are correct

### Support

For issues, questions, or feature requests:
1. Check this documentation first
2. Review the test_system.py file for usage examples
3. Examine the database schema for data structure questions
4. Test with sample data to isolate issues

## License

This project is provided as-is for educational and business use. Modify and adapt as needed for your specific requirements.

## Version History

- **v1.0**: Initial release with full collection management features
  - Priority-based collection system
  - Payment and promise tracking
  - Efficiency analytics and reporting
  - Complete customer and invoice management