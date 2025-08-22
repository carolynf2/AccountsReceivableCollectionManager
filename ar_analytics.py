"""
Collection Efficiency Analytics and Reporting
Advanced analytics for measuring and improving collection performance
"""

import sqlite3
import json
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple, Optional, Any
import logging
import math


class CollectionAnalytics:
    def __init__(self, db_path: str = "ar_collection.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.logger = logging.getLogger(__name__)
    
    def calculate_collection_efficiency_index(self, start_date: str, end_date: str) -> Dict:
        """Calculate Collection Efficiency Index (CEI) for a period"""
        self.logger.info(f"Calculating CEI for period {start_date} to {end_date}")
        
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD"}
        
        # CEI = (Beginning AR + Period Sales - Ending AR) / (Beginning AR + Period Sales) * 100
        
        # Get beginning AR (AR balance at start of period)
        self.cursor.execute("""
            SELECT SUM(outstanding_amount)
            FROM invoices
            WHERE due_date < ? AND outstanding_amount > 0
        """, (start_dt,))
        beginning_ar = float(self.cursor.fetchone()[0] or 0)
        
        # Get period sales (invoices created during period)
        self.cursor.execute("""
            SELECT SUM(invoice_amount)
            FROM invoices
            WHERE invoice_date >= ? AND invoice_date <= ?
        """, (start_dt, end_dt))
        period_sales = float(self.cursor.fetchone()[0] or 0)
        
        # Get ending AR (AR balance at end of period)
        self.cursor.execute("""
            SELECT SUM(outstanding_amount)
            FROM invoices
            WHERE due_date <= ? AND outstanding_amount > 0
        """, (end_dt,))
        ending_ar = float(self.cursor.fetchone()[0] or 0)
        
        # Calculate CEI
        denominator = beginning_ar + period_sales
        if denominator > 0:
            cei = ((beginning_ar + period_sales - ending_ar) / denominator) * 100
        else:
            cei = 0
        
        # Get cash collected during period
        self.cursor.execute("""
            SELECT SUM(payment_amount)
            FROM payments
            WHERE payment_date >= ? AND payment_date <= ?
        """, (start_dt, end_dt))
        cash_collected = float(self.cursor.fetchone()[0] or 0)
        
        return {
            "period_start": start_date,
            "period_end": end_date,
            "beginning_ar": beginning_ar,
            "period_sales": period_sales,
            "ending_ar": ending_ar,
            "cash_collected": cash_collected,
            "collection_efficiency_index": round(cei, 2),
            "cei_rating": self._get_cei_rating(cei)
        }
    
    def _get_cei_rating(self, cei: float) -> str:
        """Get qualitative rating for CEI score"""
        if cei >= 95:
            return "EXCELLENT"
        elif cei >= 85:
            return "GOOD"
        elif cei >= 75:
            return "FAIR"
        elif cei >= 65:
            return "POOR"
        else:
            return "CRITICAL"
    
    def calculate_days_sales_outstanding(self, as_of_date: str = None) -> Dict:
        """Calculate Days Sales Outstanding (DSO)"""
        if as_of_date is None:
            as_of_date = datetime.now().date()
        else:
            try:
                as_of_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Invalid date format. Use YYYY-MM-DD"}
        
        self.logger.info(f"Calculating DSO as of {as_of_date}")
        
        # Get current AR balance
        self.cursor.execute("""
            SELECT SUM(outstanding_amount)
            FROM invoices
            WHERE outstanding_amount > 0 AND due_date <= ?
        """, (as_of_date,))
        current_ar = float(self.cursor.fetchone()[0] or 0)
        
        # Get sales for last 90 days (or available period)
        ninety_days_ago = as_of_date - timedelta(days=90)
        self.cursor.execute("""
            SELECT SUM(invoice_amount)
            FROM invoices
            WHERE invoice_date >= ? AND invoice_date <= ?
        """, (ninety_days_ago, as_of_date))
        sales_90_days = float(self.cursor.fetchone()[0] or 0)
        
        # Calculate DSO
        if sales_90_days > 0:
            daily_sales = sales_90_days / 90
            dso = current_ar / daily_sales
        else:
            dso = 0
        
        # Get industry benchmark (placeholder - would typically come from external data)
        industry_benchmark = 45.0  # Typical B2B benchmark
        
        # Calculate rolling 12-month DSO for trend analysis
        twelve_months_ago = as_of_date - timedelta(days=365)
        self.cursor.execute("""
            SELECT SUM(invoice_amount)
            FROM invoices
            WHERE invoice_date >= ? AND invoice_date <= ?
        """, (twelve_months_ago, as_of_date))
        sales_12_months = float(self.cursor.fetchone()[0] or 0)
        
        if sales_12_months > 0:
            daily_sales_12m = sales_12_months / 365
            dso_12m = current_ar / daily_sales_12m
        else:
            dso_12m = 0
        
        return {
            "as_of_date": as_of_date.isoformat(),
            "current_ar_balance": current_ar,
            "sales_last_90_days": sales_90_days,
            "days_sales_outstanding": round(dso, 1),
            "dso_12_month_basis": round(dso_12m, 1),
            "industry_benchmark": industry_benchmark,
            "performance_vs_benchmark": round(dso - industry_benchmark, 1),
            "dso_rating": self._get_dso_rating(dso, industry_benchmark)
        }
    
    def _get_dso_rating(self, dso: float, benchmark: float) -> str:
        """Get qualitative rating for DSO performance"""
        if dso <= benchmark * 0.8:
            return "EXCELLENT"
        elif dso <= benchmark:
            return "GOOD"
        elif dso <= benchmark * 1.2:
            return "FAIR"
        elif dso <= benchmark * 1.5:
            return "POOR"
        else:
            return "CRITICAL"
    
    def generate_aging_analysis(self, as_of_date: str = None) -> Dict:
        """Generate comprehensive aging analysis"""
        if as_of_date is None:
            as_of_date = datetime.now().date()
        else:
            try:
                as_of_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Invalid date format. Use YYYY-MM-DD"}
        
        self.logger.info(f"Generating aging analysis as of {as_of_date}")
        
        # Update aging buckets first
        self._update_aging_buckets(as_of_date)
        
        # Get aging summary
        self.cursor.execute("""
            SELECT 
                aging_bucket,
                COUNT(*) as invoice_count,
                SUM(outstanding_amount) as total_amount,
                AVG(outstanding_amount) as avg_amount,
                MIN(outstanding_amount) as min_amount,
                MAX(outstanding_amount) as max_amount
            FROM invoices
            WHERE outstanding_amount > 0
            GROUP BY aging_bucket
            ORDER BY 
                CASE aging_bucket
                    WHEN 'CURRENT' THEN 1
                    WHEN '1-30' THEN 2
                    WHEN '31-60' THEN 3
                    WHEN '61-90' THEN 4
                    WHEN '91-120' THEN 5
                    WHEN '120+' THEN 6
                    ELSE 7
                END
        """)
        
        aging_buckets = []
        total_ar = 0
        total_invoices = 0
        
        for row in self.cursor.fetchall():
            bucket_data = {
                'aging_bucket': row[0],
                'invoice_count': row[1],
                'total_amount': float(row[2]),
                'average_amount': float(row[3]),
                'min_amount': float(row[4]),
                'max_amount': float(row[5])
            }
            aging_buckets.append(bucket_data)
            total_ar += bucket_data['total_amount']
            total_invoices += bucket_data['invoice_count']
        
        # Calculate percentages
        for bucket in aging_buckets:
            bucket['percentage_of_total'] = (bucket['total_amount'] / total_ar * 100) if total_ar > 0 else 0
        
        # Get customer distribution by aging
        self.cursor.execute("""
            SELECT 
                aging_bucket,
                COUNT(DISTINCT customer_id) as customer_count
            FROM invoices
            WHERE outstanding_amount > 0
            GROUP BY aging_bucket
        """)
        
        customer_distribution = {}
        for row in self.cursor.fetchall():
            customer_distribution[row[0]] = row[1]
        
        # Calculate concentration analysis (top customers by aging bucket)
        concentration_analysis = {}
        for bucket in ['31-60', '61-90', '91-120', '120+']:  # Focus on past due buckets
            self.cursor.execute("""
                SELECT 
                    c.customer_name,
                    SUM(i.outstanding_amount) as total_amount,
                    COUNT(i.invoice_id) as invoice_count
                FROM invoices i
                JOIN customers c ON i.customer_id = c.customer_id
                WHERE i.outstanding_amount > 0 AND i.aging_bucket = ?
                GROUP BY i.customer_id, c.customer_name
                ORDER BY total_amount DESC
                LIMIT 5
            """, (bucket,))
            
            top_customers = []
            for row in self.cursor.fetchall():
                top_customers.append({
                    'customer_name': row[0],
                    'total_amount': float(row[1]),
                    'invoice_count': row[2]
                })
            
            concentration_analysis[bucket] = top_customers
        
        return {
            "as_of_date": as_of_date.isoformat(),
            "total_ar_balance": total_ar,
            "total_invoices": total_invoices,
            "aging_buckets": aging_buckets,
            "customer_distribution": customer_distribution,
            "concentration_analysis": concentration_analysis,
            "aging_metrics": {
                "current_percentage": next((b['percentage_of_total'] for b in aging_buckets if b['aging_bucket'] == 'CURRENT'), 0),
                "past_due_percentage": sum(b['percentage_of_total'] for b in aging_buckets if b['aging_bucket'] != 'CURRENT'),
                "seriously_past_due_percentage": sum(b['percentage_of_total'] for b in aging_buckets if b['aging_bucket'] in ['91-120', '120+']),
            }
        }
    
    def _update_aging_buckets(self, as_of_date: date):
        """Update aging buckets for all outstanding invoices"""
        self.cursor.execute("""
            UPDATE invoices 
            SET 
                days_past_due = CASE 
                    WHEN julianday(?) - julianday(due_date) < 0 THEN 0
                    ELSE CAST(julianday(?) - julianday(due_date) AS INTEGER)
                END,
                aging_bucket = CASE 
                    WHEN julianday(?) - julianday(due_date) <= 0 THEN 'CURRENT'
                    WHEN julianday(?) - julianday(due_date) <= 30 THEN '1-30'
                    WHEN julianday(?) - julianday(due_date) <= 60 THEN '31-60'
                    WHEN julianday(?) - julianday(due_date) <= 90 THEN '61-90'
                    WHEN julianday(?) - julianday(due_date) <= 120 THEN '91-120'
                    ELSE '120+'
                END
            WHERE outstanding_amount > 0
        """, (as_of_date, as_of_date, as_of_date, as_of_date, as_of_date, as_of_date, as_of_date))
        self.conn.commit()
    
    def calculate_collector_performance(self, start_date: str, end_date: str) -> Dict:
        """Calculate performance metrics for collection staff"""
        self.logger.info(f"Calculating collector performance for {start_date} to {end_date}")
        
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD"}
        
        # Get collection activities by collector
        self.cursor.execute("""
            SELECT 
                performed_by,
                COUNT(*) as total_activities,
                COUNT(CASE WHEN activity_type = 'PHONE_CALL' THEN 1 END) as phone_calls,
                COUNT(CASE WHEN activity_type = 'EMAIL' THEN 1 END) as emails,
                COUNT(CASE WHEN activity_result = 'CONTACT_MADE' THEN 1 END) as successful_contacts,
                COUNT(CASE WHEN activity_result = 'PROMISE_MADE' THEN 1 END) as promises_received,
                AVG(CASE WHEN activity_type = 'PHONE_CALL' AND duration_minutes > 0 THEN duration_minutes END) as avg_call_duration
            FROM collection_activities
            WHERE activity_date >= ? AND activity_date <= ?
                AND performed_by != 'System'
            GROUP BY performed_by
        """, (start_dt, end_dt))
        
        collector_activities = {}
        for row in self.cursor.fetchall():
            collector_activities[row[0]] = {
                'total_activities': row[1],
                'phone_calls': row[2],
                'emails': row[3],
                'successful_contacts': row[4],
                'promises_received': row[5],
                'avg_call_duration': round(float(row[6]), 1) if row[6] else 0,
                'contact_success_rate': (row[4] / row[1]) * 100 if row[1] > 0 else 0
            }
        
        # Get payments collected by assignee (approximate based on activities)
        self.cursor.execute("""
            SELECT 
                ca.performed_by,
                SUM(p.payment_amount) as cash_collected,
                COUNT(DISTINCT p.payment_id) as payments_received
            FROM collection_activities ca
            JOIN invoices i ON ca.invoice_id = i.invoice_id
            JOIN payment_applications pa ON i.invoice_id = pa.invoice_id
            JOIN payments p ON pa.payment_id = p.payment_id
            WHERE ca.activity_date >= ? AND ca.activity_date <= ?
                AND p.payment_date BETWEEN ca.activity_date AND date(ca.activity_date, '+7 days')
                AND ca.performed_by != 'System'
            GROUP BY ca.performed_by
        """, (start_dt, end_dt))
        
        collector_collections = {}
        for row in self.cursor.fetchall():
            collector_collections[row[0]] = {
                'cash_collected': float(row[1]),
                'payments_received': row[2]
            }
        
        # Combine activity and collection data
        performance_data = {}
        all_collectors = set(collector_activities.keys()) | set(collector_collections.keys())
        
        for collector in all_collectors:
            activity_data = collector_activities.get(collector, {})
            collection_data = collector_collections.get(collector, {})
            
            total_activities = activity_data.get('total_activities', 0)
            cash_collected = collection_data.get('cash_collected', 0)
            
            performance_data[collector] = {
                **activity_data,
                'cash_collected': cash_collected,
                'payments_received': collection_data.get('payments_received', 0),
                'efficiency_ratio': cash_collected / total_activities if total_activities > 0 else 0,
                'performance_score': self._calculate_collector_score(activity_data, collection_data)
            }
        
        return {
            "period_start": start_date,
            "period_end": end_date,
            "collector_performance": performance_data,
            "team_summary": self._calculate_team_summary(performance_data)
        }
    
    def _calculate_collector_score(self, activity_data: Dict, collection_data: Dict) -> float:
        """Calculate performance score for a collector (0-100)"""
        score = 50  # Base score
        
        # Activity volume (0-20 points)
        total_activities = activity_data.get('total_activities', 0)
        if total_activities >= 50:
            score += 20
        elif total_activities >= 30:
            score += 15
        elif total_activities >= 20:
            score += 10
        elif total_activities >= 10:
            score += 5
        
        # Contact success rate (0-25 points)
        contact_rate = activity_data.get('contact_success_rate', 0)
        score += min(25, contact_rate * 0.4)
        
        # Cash collection (0-30 points)
        cash_collected = collection_data.get('cash_collected', 0)
        if cash_collected >= 100000:
            score += 30
        elif cash_collected >= 50000:
            score += 25
        elif cash_collected >= 25000:
            score += 20
        elif cash_collected >= 10000:
            score += 15
        elif cash_collected >= 5000:
            score += 10
        elif cash_collected > 0:
            score += 5
        
        # Promise conversion (0-15 points)
        promises = activity_data.get('promises_received', 0)
        total_activities = activity_data.get('total_activities', 0)
        if total_activities > 0:
            promise_rate = promises / total_activities
            score += min(15, promise_rate * 100)
        
        # Efficiency bonus/penalty (0-10 points)
        efficiency = collection_data.get('cash_collected', 0) / max(1, total_activities)
        if efficiency >= 2000:
            score += 10
        elif efficiency >= 1000:
            score += 5
        elif efficiency < 100:
            score -= 5
        
        return min(100, max(0, score))
    
    def _calculate_team_summary(self, performance_data: Dict) -> Dict:
        """Calculate team-wide summary statistics"""
        if not performance_data:
            return {}
        
        total_activities = sum(p.get('total_activities', 0) for p in performance_data.values())
        total_cash = sum(p.get('cash_collected', 0) for p in performance_data.values())
        total_contacts = sum(p.get('successful_contacts', 0) for p in performance_data.values())
        total_promises = sum(p.get('promises_received', 0) for p in performance_data.values())
        
        collector_count = len(performance_data)
        avg_score = sum(p.get('performance_score', 0) for p in performance_data.values()) / collector_count
        
        return {
            'total_collectors': collector_count,
            'total_activities': total_activities,
            'total_cash_collected': total_cash,
            'total_successful_contacts': total_contacts,
            'total_promises_received': total_promises,
            'team_contact_rate': (total_contacts / total_activities * 100) if total_activities > 0 else 0,
            'team_promise_rate': (total_promises / total_activities * 100) if total_activities > 0 else 0,
            'average_performance_score': round(avg_score, 1),
            'cash_per_activity': total_cash / total_activities if total_activities > 0 else 0
        }
    
    def generate_trend_analysis(self, months_back: int = 12) -> Dict:
        """Generate trend analysis for key collection metrics"""
        self.logger.info(f"Generating trend analysis for {months_back} months")
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=months_back * 30)  # Approximate
        
        # Generate monthly data points
        monthly_data = []
        current_date = start_date.replace(day=1)  # Start of month
        
        while current_date <= end_date:
            # Calculate month end date
            if current_date.month == 12:
                month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
            
            month_end = min(month_end, end_date)  # Don't go beyond current date
            
            # Calculate metrics for this month
            monthly_metrics = self._calculate_monthly_metrics(current_date, month_end)
            monthly_metrics['month'] = current_date.strftime('%Y-%m')
            monthly_data.append(monthly_metrics)
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        # Calculate trends
        trends = self._calculate_trend_direction(monthly_data)
        
        return {
            "analysis_period_months": months_back,
            "monthly_data": monthly_data,
            "trends": trends,
            "summary": self._generate_trend_summary(monthly_data, trends)
        }
    
    def _calculate_monthly_metrics(self, start_date: date, end_date: date) -> Dict:
        """Calculate key metrics for a specific month"""
        # AR balance at month end
        self.cursor.execute("""
            SELECT SUM(outstanding_amount)
            FROM invoices
            WHERE outstanding_amount > 0 AND due_date <= ?
        """, (end_date,))
        ar_balance = float(self.cursor.fetchone()[0] or 0)
        
        # Cash collected during month
        self.cursor.execute("""
            SELECT SUM(payment_amount)
            FROM payments
            WHERE payment_date >= ? AND payment_date <= ?
        """, (start_date, end_date))
        cash_collected = float(self.cursor.fetchone()[0] or 0)
        
        # New invoices during month
        self.cursor.execute("""
            SELECT SUM(invoice_amount)
            FROM invoices
            WHERE invoice_date >= ? AND invoice_date <= ?
        """, (start_date, end_date))
        new_invoices = float(self.cursor.fetchone()[0] or 0)
        
        # Collection activities during month
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM collection_activities
            WHERE activity_date >= ? AND activity_date <= ?
        """, (start_date, end_date))
        collection_activities = self.cursor.fetchone()[0] or 0
        
        # Past due amount
        self.cursor.execute("""
            SELECT SUM(outstanding_amount)
            FROM invoices
            WHERE outstanding_amount > 0 AND due_date < ? AND due_date <= ?
        """, (end_date, end_date))
        past_due_amount = float(self.cursor.fetchone()[0] or 0)
        
        # Calculate DSO for month end
        sales_90_days_ago = end_date - timedelta(days=90)
        self.cursor.execute("""
            SELECT SUM(invoice_amount)
            FROM invoices
            WHERE invoice_date >= ? AND invoice_date <= ?
        """, (sales_90_days_ago, end_date))
        sales_90_days = float(self.cursor.fetchone()[0] or 0)
        
        dso = (ar_balance / (sales_90_days / 90)) if sales_90_days > 0 else 0
        
        return {
            'ar_balance': ar_balance,
            'cash_collected': cash_collected,
            'new_invoices': new_invoices,
            'collection_activities': collection_activities,
            'past_due_amount': past_due_amount,
            'past_due_percentage': (past_due_amount / ar_balance * 100) if ar_balance > 0 else 0,
            'dso': round(dso, 1),
            'collection_ratio': (cash_collected / ar_balance * 100) if ar_balance > 0 else 0
        }
    
    def _calculate_trend_direction(self, monthly_data: List[Dict]) -> Dict:
        """Calculate trend direction for key metrics"""
        if len(monthly_data) < 2:
            return {}
        
        trends = {}
        metrics = ['ar_balance', 'cash_collected', 'dso', 'past_due_percentage']
        
        for metric in metrics:
            values = [month.get(metric, 0) for month in monthly_data if metric in month]
            if len(values) >= 2:
                # Simple linear trend
                recent_avg = sum(values[-3:]) / min(3, len(values))
                earlier_avg = sum(values[:3]) / min(3, len(values))
                
                if recent_avg > earlier_avg * 1.05:
                    direction = "INCREASING"
                elif recent_avg < earlier_avg * 0.95:
                    direction = "DECREASING"
                else:
                    direction = "STABLE"
                
                change_pct = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg > 0 else 0
                
                trends[metric] = {
                    'direction': direction,
                    'change_percentage': round(change_pct, 1),
                    'recent_average': round(recent_avg, 2),
                    'earlier_average': round(earlier_avg, 2)
                }
        
        return trends
    
    def _generate_trend_summary(self, monthly_data: List[Dict], trends: Dict) -> Dict:
        """Generate summary of trend analysis"""
        if not monthly_data:
            return {}
        
        latest_month = monthly_data[-1]
        
        summary = {
            'current_ar_balance': latest_month.get('ar_balance', 0),
            'current_dso': latest_month.get('dso', 0),
            'current_past_due_pct': latest_month.get('past_due_percentage', 0),
            'recommendations': []
        }
        
        # Generate recommendations based on trends
        ar_trend = trends.get('ar_balance', {})
        if ar_trend.get('direction') == 'INCREASING' and ar_trend.get('change_percentage', 0) > 10:
            summary['recommendations'].append("AR balance is increasing significantly - review credit and collection policies")
        
        dso_trend = trends.get('dso', {})
        if dso_trend.get('direction') == 'INCREASING':
            summary['recommendations'].append("DSO is trending upward - implement more aggressive collection procedures")
        
        past_due_trend = trends.get('past_due_percentage', {})
        if past_due_trend.get('direction') == 'INCREASING':
            summary['recommendations'].append("Past due percentage is increasing - focus on early intervention strategies")
        
        cash_trend = trends.get('cash_collected', {})
        if cash_trend.get('direction') == 'DECREASING':
            summary['recommendations'].append("Cash collection is declining - review collection team performance and processes")
        
        if not summary['recommendations']:
            summary['recommendations'].append("Collection metrics are stable - continue current strategies")
        
        return summary
    
    def generate_comprehensive_dashboard(self, as_of_date: str = None) -> Dict:
        """Generate comprehensive collection dashboard"""
        if as_of_date is None:
            as_of_date = datetime.now().date().isoformat()
        
        self.logger.info(f"Generating comprehensive dashboard as of {as_of_date}")
        
        # Get key metrics
        dso_data = self.calculate_days_sales_outstanding(as_of_date)
        aging_data = self.generate_aging_analysis(as_of_date)
        
        # Calculate 30-day CEI
        end_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        start_date = end_date - timedelta(days=30)
        cei_data = self.calculate_collection_efficiency_index(start_date.isoformat(), as_of_date)
        
        # Get performance data
        collector_data = self.calculate_collector_performance(start_date.isoformat(), as_of_date)
        
        # Get activity summary
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_activities,
                COUNT(CASE WHEN activity_result = 'CONTACT_MADE' THEN 1 END) as successful_contacts,
                COUNT(CASE WHEN activity_result = 'PROMISE_MADE' THEN 1 END) as promises_made,
                COUNT(DISTINCT customer_id) as customers_contacted
            FROM collection_activities
            WHERE activity_date >= ? AND activity_date <= ?
        """, (start_date, end_date))
        
        activity_summary = self.cursor.fetchone()
        
        # Get promise performance
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_promises,
                COUNT(CASE WHEN status = 'KEPT' THEN 1 END) as kept_promises,
                COUNT(CASE WHEN status = 'BROKEN' THEN 1 END) as broken_promises,
                SUM(promised_amount) as total_promised,
                SUM(actual_payment_amount) as total_received
            FROM payment_promises
            WHERE promise_date >= ? AND promise_date <= ?
        """, (start_date, end_date))
        
        promise_summary = self.cursor.fetchone()
        
        return {
            "dashboard_date": as_of_date,
            "period_days": 30,
            "key_metrics": {
                "days_sales_outstanding": dso_data.get('days_sales_outstanding', 0),
                "dso_rating": dso_data.get('dso_rating', 'N/A'),
                "collection_efficiency_index": cei_data.get('collection_efficiency_index', 0),
                "cei_rating": cei_data.get('cei_rating', 'N/A'),
                "total_ar_balance": aging_data.get('total_ar_balance', 0),
                "past_due_percentage": aging_data.get('aging_metrics', {}).get('past_due_percentage', 0),
                "seriously_past_due_percentage": aging_data.get('aging_metrics', {}).get('seriously_past_due_percentage', 0)
            },
            "aging_summary": {
                "current": next((b['total_amount'] for b in aging_data.get('aging_buckets', []) if b['aging_bucket'] == 'CURRENT'), 0),
                "1_30_days": next((b['total_amount'] for b in aging_data.get('aging_buckets', []) if b['aging_bucket'] == '1-30'), 0),
                "31_60_days": next((b['total_amount'] for b in aging_data.get('aging_buckets', []) if b['aging_bucket'] == '31-60'), 0),
                "61_90_days": next((b['total_amount'] for b in aging_data.get('aging_buckets', []) if b['aging_bucket'] == '61-90'), 0),
                "over_90_days": sum(b['total_amount'] for b in aging_data.get('aging_buckets', []) if b['aging_bucket'] in ['91-120', '120+'])
            },
            "activity_summary": {
                "total_activities": activity_summary[0] if activity_summary else 0,
                "successful_contacts": activity_summary[1] if activity_summary else 0,
                "promises_made": activity_summary[2] if activity_summary else 0,
                "customers_contacted": activity_summary[3] if activity_summary else 0,
                "contact_success_rate": (activity_summary[1] / activity_summary[0] * 100) if activity_summary and activity_summary[0] > 0 else 0
            },
            "promise_performance": {
                "total_promises": promise_summary[0] if promise_summary else 0,
                "kept_promises": promise_summary[1] if promise_summary else 0,
                "broken_promises": promise_summary[2] if promise_summary else 0,
                "promise_keep_rate": (promise_summary[1] / promise_summary[0] * 100) if promise_summary and promise_summary[0] > 0 else 0,
                "total_promised": float(promise_summary[3]) if promise_summary and promise_summary[3] else 0,
                "total_received": float(promise_summary[4]) if promise_summary and promise_summary[4] else 0
            },
            "team_performance": collector_data.get('team_summary', {}),
            "generated_timestamp": datetime.now().isoformat()
        }
    
    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == "__main__":
    # Example usage
    analytics = CollectionAnalytics()
    try:
        # Generate comprehensive dashboard
        dashboard = analytics.generate_comprehensive_dashboard()
        
        print("Collection Dashboard Summary:")
        print(f"DSO: {dashboard['key_metrics']['days_sales_outstanding']} days ({dashboard['key_metrics']['dso_rating']})")
        print(f"CEI: {dashboard['key_metrics']['collection_efficiency_index']}% ({dashboard['key_metrics']['cei_rating']})")
        print(f"Total AR: ${dashboard['key_metrics']['total_ar_balance']:,.2f}")
        print(f"Past Due: {dashboard['key_metrics']['past_due_percentage']:.1f}%")
        print(f"Contact Success Rate: {dashboard['activity_summary']['contact_success_rate']:.1f}%")
        print(f"Promise Keep Rate: {dashboard['promise_performance']['promise_keep_rate']:.1f}%")
        
    finally:
        analytics.close()