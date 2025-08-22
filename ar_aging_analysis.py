"""
Accounts Receivable Aging Analysis and Reporting
Comprehensive aging analysis with detailed reporting and trend analysis
"""

import sqlite3
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from decimal import Decimal
import json

@dataclass
class AgingBucket:
    bucket_name: str
    min_days: int
    max_days: Optional[int]
    amount: Decimal
    invoice_count: int
    percentage: float

@dataclass
class CustomerAgingProfile:
    customer_id: int
    customer_name: str
    customer_code: str
    total_outstanding: Decimal
    current_amount: Decimal
    aging_buckets: Dict[str, Decimal]
    largest_invoice_amount: Decimal
    oldest_invoice_days: int
    average_days_outstanding: float
    risk_score: int

class AgingAnalyzer:
    def __init__(self, db_path: str = "ar_collection.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        self.aging_buckets = {
            'CURRENT': (0, 0),
            '1-30': (1, 30),
            '31-60': (31, 60),
            '61-90': (61, 90),
            '91-120': (91, 120),
            '120+': (121, None)
        }

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def calculate_invoice_aging(self, as_of_date: Optional[date] = None) -> None:
        """Calculate and update aging information for all invoices"""
        if not as_of_date:
            as_of_date = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Update days past due and aging buckets for all open invoices
            cursor.execute("""
                UPDATE invoices 
                SET days_past_due = CAST((julianday(?) - julianday(due_date)) AS INTEGER),
                    aging_bucket = CASE 
                        WHEN CAST((julianday(?) - julianday(due_date)) AS INTEGER) <= 0 THEN 'CURRENT'
                        WHEN CAST((julianday(?) - julianday(due_date)) AS INTEGER) BETWEEN 1 AND 30 THEN '1-30'
                        WHEN CAST((julianday(?) - julianday(due_date)) AS INTEGER) BETWEEN 31 AND 60 THEN '31-60'
                        WHEN CAST((julianday(?) - julianday(due_date)) AS INTEGER) BETWEEN 61 AND 90 THEN '61-90'
                        WHEN CAST((julianday(?) - julianday(due_date)) AS INTEGER) BETWEEN 91 AND 120 THEN '91-120'
                        ELSE '120+'
                    END
                WHERE status IN ('OPEN', 'PARTIAL')
            """, (as_of_date,) * 6)
            
            conn.commit()
            
        self.logger.info(f"Updated aging calculations as of {as_of_date}")

    def generate_aging_report(self, as_of_date: Optional[date] = None,
                            customer_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate comprehensive aging report"""
        if not as_of_date:
            as_of_date = datetime.now().date()
        
        # Ensure aging is current
        self.calculate_invoice_aging(as_of_date)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Base query conditions
            where_conditions = ["i.status IN ('OPEN', 'PARTIAL')"]
            params = []
            
            if customer_id:
                where_conditions.append("i.customer_id = ?")
                params.append(customer_id)
            
            where_clause = " AND ".join(where_conditions)
            
            # Overall aging summary
            cursor.execute(f"""
                SELECT 
                    i.aging_bucket,
                    COUNT(*) as invoice_count,
                    SUM(i.outstanding_amount) as total_amount,
                    AVG(i.outstanding_amount) as avg_amount,
                    MIN(i.outstanding_amount) as min_amount,
                    MAX(i.outstanding_amount) as max_amount
                FROM invoices i
                WHERE {where_clause}
                GROUP BY i.aging_bucket
                ORDER BY 
                    CASE i.aging_bucket
                        WHEN 'CURRENT' THEN 1
                        WHEN '1-30' THEN 2
                        WHEN '31-60' THEN 3
                        WHEN '61-90' THEN 4
                        WHEN '91-120' THEN 5
                        WHEN '120+' THEN 6
                    END
            """, params)
            
            aging_summary = {}
            total_outstanding = Decimal('0')
            total_invoices = 0
            
            for row in cursor.fetchall():
                bucket, count, amount, avg_amt, min_amt, max_amt = row
                amount = Decimal(str(amount or 0))
                total_outstanding += amount
                total_invoices += count
                
                aging_summary[bucket] = {
                    'invoice_count': count,
                    'total_amount': float(amount),
                    'average_amount': float(avg_amt or 0),
                    'min_amount': float(min_amt or 0),
                    'max_amount': float(max_amt or 0)
                }
            
            # Calculate percentages
            for bucket in aging_summary:
                if total_outstanding > 0:
                    aging_summary[bucket]['percentage'] = (
                        aging_summary[bucket]['total_amount'] / float(total_outstanding) * 100
                    )
                else:
                    aging_summary[bucket]['percentage'] = 0
            
            # Customer-level aging analysis
            cursor.execute(f"""
                SELECT 
                    c.customer_id,
                    c.customer_name,
                    c.customer_code,
                    c.customer_type,
                    SUM(i.outstanding_amount) as total_outstanding,
                    COUNT(i.invoice_id) as invoice_count,
                    AVG(i.days_past_due) as avg_days_outstanding,
                    MAX(i.days_past_due) as max_days_outstanding,
                    MAX(i.outstanding_amount) as largest_invoice
                FROM customers c
                JOIN invoices i ON c.customer_id = i.customer_id
                WHERE {where_clause}
                GROUP BY c.customer_id, c.customer_name, c.customer_code, c.customer_type
                HAVING SUM(i.outstanding_amount) > 0
                ORDER BY total_outstanding DESC
            """, params)
            
            customer_analysis = []
            for row in cursor.fetchall():
                cust_id, name, code, cust_type, outstanding, inv_count, avg_days, max_days, largest = row
                
                # Get customer's aging breakdown
                cursor.execute("""
                    SELECT aging_bucket, SUM(outstanding_amount)
                    FROM invoices
                    WHERE customer_id = ? AND status IN ('OPEN', 'PARTIAL')
                    GROUP BY aging_bucket
                """, (cust_id,))
                
                customer_buckets = dict(cursor.fetchall())
                
                customer_analysis.append({
                    'customer_id': cust_id,
                    'customer_name': name,
                    'customer_code': code,
                    'customer_type': cust_type,
                    'total_outstanding': float(outstanding or 0),
                    'invoice_count': inv_count,
                    'avg_days_outstanding': float(avg_days or 0),
                    'max_days_outstanding': max_days or 0,
                    'largest_invoice': float(largest or 0),
                    'aging_breakdown': {
                        bucket: float(customer_buckets.get(bucket, 0))
                        for bucket in self.aging_buckets.keys()
                    }
                })
            
            # Risk analysis
            risk_analysis = self._calculate_aging_risk_metrics(cursor, where_clause, params)
            
            return {
                'report_date': as_of_date.isoformat(),
                'summary': {
                    'total_outstanding': float(total_outstanding),
                    'total_invoices': total_invoices,
                    'aging_buckets': aging_summary
                },
                'customer_analysis': customer_analysis,
                'risk_analysis': risk_analysis
            }

    def _calculate_aging_risk_metrics(self, cursor, where_clause: str, params: List) -> Dict[str, Any]:
        """Calculate risk metrics based on aging analysis"""
        
        # Concentration risk - top customers by outstanding amount
        cursor.execute(f"""
            SELECT 
                c.customer_name,
                SUM(i.outstanding_amount) as outstanding,
                (SUM(i.outstanding_amount) * 100.0 / (
                    SELECT SUM(outstanding_amount) 
                    FROM invoices 
                    WHERE {where_clause}
                )) as concentration_percentage
            FROM customers c
            JOIN invoices i ON c.customer_id = i.customer_id
            WHERE {where_clause}
            GROUP BY c.customer_id, c.customer_name
            ORDER BY outstanding DESC
            LIMIT 10
        """, params)
        
        concentration_risk = [
            {
                'customer_name': row[0],
                'outstanding_amount': float(row[1] or 0),
                'concentration_percentage': float(row[2] or 0)
            }
            for row in cursor.fetchall()
        ]
        
        # Aging trend risk
        cursor.execute(f"""
            SELECT 
                COUNT(CASE WHEN aging_bucket IN ('61-90', '91-120', '120+') THEN 1 END) as high_risk_invoices,
                SUM(CASE WHEN aging_bucket IN ('61-90', '91-120', '120+') THEN outstanding_amount ELSE 0 END) as high_risk_amount,
                COUNT(*) as total_invoices,
                SUM(outstanding_amount) as total_amount
            FROM invoices i
            WHERE {where_clause}
        """, params)
        
        risk_row = cursor.fetchone()
        high_risk_invoices, high_risk_amount, total_invoices, total_amount = risk_row
        
        aging_risk = {
            'high_risk_invoices': high_risk_invoices or 0,
            'high_risk_amount': float(high_risk_amount or 0),
            'high_risk_invoice_percentage': (
                (high_risk_invoices or 0) / (total_invoices or 1) * 100
            ),
            'high_risk_amount_percentage': (
                float(high_risk_amount or 0) / float(total_amount or 1) * 100
            )
        }
        
        # Collection efficiency by aging bucket
        cursor.execute(f"""
            SELECT 
                i.aging_bucket,
                COUNT(CASE WHEN ca.activity_date >= date('now', '-30 days') THEN 1 END) as recent_activities,
                COUNT(i.invoice_id) as total_invoices
            FROM invoices i
            LEFT JOIN collection_activities ca ON i.invoice_id = ca.invoice_id
            WHERE {where_clause}
            GROUP BY i.aging_bucket
        """, params)
        
        collection_coverage = {}
        for bucket, activities, invoices in cursor.fetchall():
            collection_coverage[bucket] = {
                'invoices_with_recent_activity': activities or 0,
                'total_invoices': invoices,
                'coverage_percentage': (
                    (activities or 0) / (invoices or 1) * 100
                )
            }
        
        return {
            'concentration_risk': concentration_risk,
            'aging_risk': aging_risk,
            'collection_coverage': collection_coverage
        }

    def generate_trend_analysis(self, months_back: int = 12) -> Dict[str, Any]:
        """Generate aging trend analysis over time"""
        end_date = datetime.now().date()
        trends = []
        
        for month in range(months_back):
            analysis_date = end_date - timedelta(days=30 * month)
            
            # Calculate aging as of that date
            self.calculate_invoice_aging(analysis_date)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get aging summary for that date
                cursor.execute("""
                    SELECT 
                        aging_bucket,
                        SUM(outstanding_amount) as amount
                    FROM invoices
                    WHERE status IN ('OPEN', 'PARTIAL')
                    AND invoice_date <= ?
                    GROUP BY aging_bucket
                """, (analysis_date,))
                
                bucket_amounts = dict(cursor.fetchall())
                total_amount = sum(bucket_amounts.values())
                
                trend_data = {
                    'date': analysis_date.isoformat(),
                    'total_outstanding': float(total_amount),
                    'buckets': {}
                }
                
                for bucket in self.aging_buckets.keys():
                    amount = float(bucket_amounts.get(bucket, 0))
                    percentage = (amount / total_amount * 100) if total_amount > 0 else 0
                    
                    trend_data['buckets'][bucket] = {
                        'amount': amount,
                        'percentage': percentage
                    }
                
                trends.append(trend_data)
        
        # Calculate month-over-month changes
        if len(trends) >= 2:
            current = trends[0]
            previous = trends[1]
            
            changes = {
                'total_outstanding_change': (
                    current['total_outstanding'] - previous['total_outstanding']
                ),
                'total_outstanding_change_percentage': (
                    (current['total_outstanding'] - previous['total_outstanding']) /
                    (previous['total_outstanding'] or 1) * 100
                ),
                'bucket_changes': {}
            }
            
            for bucket in self.aging_buckets.keys():
                current_amount = current['buckets'][bucket]['amount']
                previous_amount = previous['buckets'][bucket]['amount']
                
                changes['bucket_changes'][bucket] = {
                    'amount_change': current_amount - previous_amount,
                    'percentage_change': (
                        (current_amount - previous_amount) / (previous_amount or 1) * 100
                    )
                }
        else:
            changes = {}
        
        return {
            'analysis_period': f"{months_back} months",
            'trends': list(reversed(trends)),  # Oldest to newest
            'month_over_month_changes': changes
        }

    def get_collection_priorities_by_aging(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get prioritized list of invoices for collection based on aging"""
        self.calculate_invoice_aging()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    i.invoice_id,
                    i.invoice_number,
                    c.customer_id,
                    c.customer_name,
                    c.customer_code,
                    i.outstanding_amount,
                    i.days_past_due,
                    i.aging_bucket,
                    i.due_date,
                    c.payment_reliability_score,
                    c.collection_priority,
                    ca.last_activity_date,
                    ca.activity_count,
                    -- Priority score calculation
                    (
                        (i.outstanding_amount / 1000.0) * 0.3 +  -- Amount weight
                        (i.days_past_due / 10.0) * 0.4 +        -- Age weight
                        (100 - c.payment_reliability_score) * 0.2 + -- Risk weight
                        CASE 
                            WHEN ca.last_activity_date IS NULL THEN 20
                            WHEN ca.last_activity_date < date('now', '-14 days') THEN 15
                            WHEN ca.last_activity_date < date('now', '-7 days') THEN 10
                            ELSE 5
                        END * 0.1  -- Recency weight
                    ) as priority_score
                FROM invoices i
                JOIN customers c ON i.customer_id = c.customer_id
                LEFT JOIN (
                    SELECT 
                        customer_id,
                        MAX(activity_date) as last_activity_date,
                        COUNT(*) as activity_count
                    FROM collection_activities
                    WHERE activity_date >= date('now', '-30 days')
                    GROUP BY customer_id
                ) ca ON c.customer_id = ca.customer_id
                WHERE i.status IN ('OPEN', 'PARTIAL')
                AND i.outstanding_amount > 0
                ORDER BY priority_score DESC
                LIMIT ?
            """, (limit,))
            
            priorities = []
            for row in cursor.fetchall():
                invoice_data = {
                    'invoice_id': row[0],
                    'invoice_number': row[1],
                    'customer_id': row[2],
                    'customer_name': row[3],
                    'customer_code': row[4],
                    'outstanding_amount': float(row[5]),
                    'days_past_due': row[6],
                    'aging_bucket': row[7],
                    'due_date': row[8],
                    'payment_reliability_score': row[9],
                    'collection_priority': row[10],
                    'last_activity_date': row[11],
                    'recent_activity_count': row[12] or 0,
                    'priority_score': float(row[13])
                }
                
                # Add recommended actions based on aging bucket
                if row[7] == 'CURRENT':
                    invoice_data['recommended_action'] = 'Monitor - payment not yet due'
                elif row[7] == '1-30':
                    invoice_data['recommended_action'] = 'Friendly reminder call or email'
                elif row[7] == '31-60':
                    invoice_data['recommended_action'] = 'Follow-up call and formal notice'
                elif row[7] == '61-90':
                    invoice_data['recommended_action'] = 'Escalate to senior collector'
                elif row[7] == '91-120':
                    invoice_data['recommended_action'] = 'Credit hold and payment arrangement'
                else:  # 120+
                    invoice_data['recommended_action'] = 'Consider legal action'
                
                priorities.append(invoice_data)
            
            return priorities

    def generate_dashboard_metrics(self) -> Dict[str, Any]:
        """Generate key aging metrics for dashboard display"""
        self.calculate_invoice_aging()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Key performance indicators
            cursor.execute("""
                SELECT 
                    SUM(outstanding_amount) as total_ar,
                    COUNT(*) as total_invoices,
                    AVG(days_past_due) as avg_days_outstanding,
                    SUM(CASE WHEN aging_bucket = 'CURRENT' THEN outstanding_amount ELSE 0 END) as current_ar,
                    SUM(CASE WHEN aging_bucket IN ('1-30', '31-60') THEN outstanding_amount ELSE 0 END) as moderately_aged_ar,
                    SUM(CASE WHEN aging_bucket IN ('61-90', '91-120', '120+') THEN outstanding_amount ELSE 0 END) as severely_aged_ar
                FROM invoices
                WHERE status IN ('OPEN', 'PARTIAL')
            """)
            
            kpi_row = cursor.fetchone()
            total_ar, total_invoices, avg_days, current_ar, moderate_ar, severe_ar = kpi_row
            
            # Collection effectiveness metrics
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN ca.activity_date >= date('now', '-7 days') THEN 1 END) as activities_this_week,
                    COUNT(CASE WHEN ca.activity_date >= date('now', '-30 days') THEN 1 END) as activities_this_month,
                    COUNT(DISTINCT CASE WHEN ca.activity_date >= date('now', '-7 days') THEN ca.customer_id END) as customers_contacted_this_week
                FROM collection_activities ca
            """)
            
            activity_row = cursor.fetchone()
            activities_week, activities_month, customers_week = activity_row
            
            # Risk indicators
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN days_past_due > 90 THEN 1 END) as high_risk_invoices,
                    COUNT(CASE WHEN outstanding_amount > 10000 AND days_past_due > 60 THEN 1 END) as large_aged_invoices,
                    COUNT(CASE WHEN aging_bucket = '120+' THEN 1 END) as extremely_aged_invoices
                FROM invoices
                WHERE status IN ('OPEN', 'PARTIAL')
            """)
            
            risk_row = cursor.fetchone()
            high_risk, large_aged, extremely_aged = risk_row
            
            return {
                'total_ar': float(total_ar or 0),
                'total_invoices': total_invoices or 0,
                'average_days_outstanding': float(avg_days or 0),
                'ar_composition': {
                    'current': float(current_ar or 0),
                    'moderately_aged': float(moderate_ar or 0),
                    'severely_aged': float(severe_ar or 0)
                },
                'ar_percentages': {
                    'current_percentage': (float(current_ar or 0) / float(total_ar or 1) * 100),
                    'moderate_percentage': (float(moderate_ar or 0) / float(total_ar or 1) * 100),
                    'severe_percentage': (float(severe_ar or 0) / float(total_ar or 1) * 100)
                },
                'collection_activity': {
                    'activities_this_week': activities_week or 0,
                    'activities_this_month': activities_month or 0,
                    'customers_contacted_this_week': customers_week or 0
                },
                'risk_indicators': {
                    'high_risk_invoices': high_risk or 0,
                    'large_aged_invoices': large_aged or 0,
                    'extremely_aged_invoices': extremely_aged or 0
                }
            }

# Usage example and testing
if __name__ == "__main__":
    analyzer = AgingAnalyzer()
    
    # Generate aging report
    aging_report = analyzer.generate_aging_report()
    print(f"Aging Report - Total Outstanding: ${aging_report['summary']['total_outstanding']:,.2f}")
    
    # Get collection priorities
    priorities = analyzer.get_collection_priorities_by_aging(limit=10)
    print(f"Top 10 collection priorities:")
    for i, priority in enumerate(priorities[:5], 1):
        print(f"{i}. {priority['customer_name']} - ${priority['outstanding_amount']:,.2f} ({priority['aging_bucket']})")
    
    # Generate trend analysis
    trends = analyzer.generate_trend_analysis(months_back=6)
    print(f"Trend analysis over 6 months shows {len(trends['trends'])} data points")
    
    # Dashboard metrics
    dashboard = analyzer.generate_dashboard_metrics()
    print(f"Dashboard: Total AR ${dashboard['total_ar']:,.2f}, Avg Days: {dashboard['average_days_outstanding']:.1f}")