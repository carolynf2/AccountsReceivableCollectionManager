"""
Customer Prioritization and Scoring Engine
Advanced algorithms for prioritizing collection efforts and scoring customers
"""

import sqlite3
import json
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple, Optional
import logging
import math


class CollectionPrioritizer:
    def __init__(self, db_path: str = "ar_collection.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.logger = logging.getLogger(__name__)
        
        # Scoring weights and parameters
        self.scoring_weights = {
            'amount_weight': 0.25,          # Invoice amount impact
            'aging_weight': 0.30,           # Days past due impact
            'customer_history_weight': 0.20,  # Payment history impact
            'relationship_weight': 0.15,    # Customer relationship value
            'collection_effort_weight': 0.10  # Previous collection effort impact
        }
        
        # Risk assessment parameters
        self.risk_thresholds = {
            'high_risk_score': 75,
            'medium_risk_score': 50,
            'low_risk_score': 25
        }
        
        # Customer value tiers
        self.value_tiers = {
            'tier_1_min': 100000,  # High value customers
            'tier_2_min': 25000,   # Medium value customers
            'tier_3_min': 5000     # Regular customers
        }
    
    def calculate_customer_priority_score(self, customer_id: int) -> Dict:
        """Calculate comprehensive priority score for a customer"""
        self.logger.info(f"Calculating priority score for customer {customer_id}")
        
        # Get customer basic information
        customer_info = self._get_customer_info(customer_id)
        if not customer_info:
            return {"error": "Customer not found"}
        
        # Get customer's outstanding invoices
        outstanding_invoices = self._get_outstanding_invoices(customer_id)
        if not outstanding_invoices:
            return {
                "customer_id": customer_id,
                "priority_score": 0,
                "risk_level": "LOW",
                "total_outstanding": 0,
                "recommendations": ["No outstanding balance"]
            }
        
        # Calculate component scores
        amount_score = self._calculate_amount_score(outstanding_invoices)
        aging_score = self._calculate_aging_score(outstanding_invoices)
        history_score = self._calculate_payment_history_score(customer_id)
        relationship_score = self._calculate_relationship_score(customer_id, customer_info)
        effort_score = self._calculate_collection_effort_score(customer_id)
        
        # Calculate weighted final score
        final_score = (
            amount_score * self.scoring_weights['amount_weight'] +
            aging_score * self.scoring_weights['aging_weight'] +
            history_score * self.scoring_weights['customer_history_weight'] +
            relationship_score * self.scoring_weights['relationship_weight'] +
            effort_score * self.scoring_weights['collection_effort_weight']
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(final_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            customer_id, customer_info, outstanding_invoices, final_score, {
                'amount': amount_score,
                'aging': aging_score,
                'history': history_score,
                'relationship': relationship_score,
                'effort': effort_score
            }
        )
        
        # Calculate additional metrics
        total_outstanding = sum(float(invoice['outstanding_amount']) for invoice in outstanding_invoices)
        oldest_invoice_days = max(invoice['days_past_due'] for invoice in outstanding_invoices)
        avg_invoice_age = sum(invoice['days_past_due'] for invoice in outstanding_invoices) / len(outstanding_invoices)
        
        return {
            "customer_id": customer_id,
            "customer_name": customer_info['customer_name'],
            "company_name": customer_info['company_name'],
            "priority_score": round(final_score, 2),
            "risk_level": risk_level,
            "total_outstanding": total_outstanding,
            "invoice_count": len(outstanding_invoices),
            "oldest_invoice_days": oldest_invoice_days,
            "avg_invoice_age": round(avg_invoice_age, 1),
            "component_scores": {
                "amount_score": round(amount_score, 2),
                "aging_score": round(aging_score, 2),
                "history_score": round(history_score, 2),
                "relationship_score": round(relationship_score, 2),
                "effort_score": round(effort_score, 2)
            },
            "recommendations": recommendations,
            "next_action": self._determine_next_action(final_score, oldest_invoice_days),
            "calculated_date": datetime.now().isoformat()
        }
    
    def _get_customer_info(self, customer_id: int) -> Optional[Dict]:
        """Get customer basic information"""
        self.cursor.execute("""
            SELECT customer_id, customer_name, company_name, customer_type,
                   credit_limit, payment_terms_days, avg_days_to_pay,
                   payment_reliability_score, total_sales_lifetime,
                   customer_since, collection_priority, is_credit_hold
            FROM customers
            WHERE customer_id = ?
        """, (customer_id,))
        
        result = self.cursor.fetchone()
        if not result:
            return None
        
        return {
            'customer_id': result[0],
            'customer_name': result[1],
            'company_name': result[2],
            'customer_type': result[3],
            'credit_limit': float(result[4]),
            'payment_terms_days': result[5],
            'avg_days_to_pay': float(result[6]),
            'payment_reliability_score': result[7],
            'total_sales_lifetime': float(result[8]),
            'customer_since': result[9],
            'collection_priority': result[10],
            'is_credit_hold': bool(result[11])
        }
    
    def _get_outstanding_invoices(self, customer_id: int) -> List[Dict]:
        """Get customer's outstanding invoices"""
        self.cursor.execute("""
            SELECT invoice_id, invoice_number, invoice_amount, outstanding_amount,
                   days_past_due, aging_bucket, collection_status, collection_priority_score,
                   invoice_date, due_date
            FROM invoices
            WHERE customer_id = ? AND outstanding_amount > 0
            ORDER BY days_past_due DESC, outstanding_amount DESC
        """, (customer_id,))
        
        results = []
        for row in self.cursor.fetchall():
            results.append({
                'invoice_id': row[0],
                'invoice_number': row[1],
                'invoice_amount': float(row[2]),
                'outstanding_amount': float(row[3]),
                'days_past_due': row[4],
                'aging_bucket': row[5],
                'collection_status': row[6],
                'collection_priority_score': row[7],
                'invoice_date': row[8],
                'due_date': row[9]
            })
        
        return results
    
    def _calculate_amount_score(self, invoices: List[Dict]) -> float:
        """Calculate score based on outstanding amounts"""
        if not invoices:
            return 0
        
        total_outstanding = sum(invoice['outstanding_amount'] for invoice in invoices)
        
        # Logarithmic scaling for amount impact
        if total_outstanding <= 1000:
            return 10
        elif total_outstanding <= 5000:
            return 25
        elif total_outstanding <= 25000:
            return 50
        elif total_outstanding <= 100000:
            return 75
        else:
            return 90
    
    def _calculate_aging_score(self, invoices: List[Dict]) -> float:
        """Calculate score based on aging of invoices"""
        if not invoices:
            return 0
        
        # Weight by both age and amount
        weighted_aging = 0
        total_weight = 0
        
        for invoice in invoices:
            amount_weight = invoice['outstanding_amount']
            days_score = min(100, invoice['days_past_due'] * 0.8)  # 0.8 points per day
            
            weighted_aging += days_score * amount_weight
            total_weight += amount_weight
        
        return weighted_aging / total_weight if total_weight > 0 else 0
    
    def _calculate_payment_history_score(self, customer_id: int) -> float:
        """Calculate score based on payment history"""
        # Get payment reliability score from customer record
        self.cursor.execute("""
            SELECT payment_reliability_score, avg_days_to_pay, payment_terms_days
            FROM customers
            WHERE customer_id = ?
        """, (customer_id,))
        
        result = self.cursor.fetchone()
        if not result:
            return 50  # Default neutral score
        
        reliability_score, avg_days_to_pay, payment_terms = result
        
        # Start with reliability score (0-100)
        history_score = reliability_score
        
        # Adjust based on payment timing vs terms
        if avg_days_to_pay <= payment_terms:
            # Pays on time or early
            history_score = min(100, history_score + 10)
        elif avg_days_to_pay <= payment_terms + 10:
            # Slightly late but acceptable
            history_score = max(0, history_score - 5)
        else:
            # Consistently late
            days_late_factor = min(50, (avg_days_to_pay - payment_terms) * 2)
            history_score = max(0, history_score - days_late_factor)
        
        # Check recent payment promise performance
        self.cursor.execute("""
            SELECT COUNT(*) as total_promises,
                   COUNT(CASE WHEN status = 'KEPT' THEN 1 END) as kept_promises
            FROM payment_promises
            WHERE customer_id = ? AND promise_date >= date('now', '-90 days')
        """, (customer_id,))
        
        promise_result = self.cursor.fetchone()
        if promise_result and promise_result[0] > 0:
            promise_rate = promise_result[1] / promise_result[0]
            if promise_rate < 0.5:
                history_score = max(0, history_score - 20)  # Poor promise keeping
            elif promise_rate > 0.8:
                history_score = min(100, history_score + 5)  # Good promise keeping
        
        return history_score
    
    def _calculate_relationship_score(self, customer_id: int, customer_info: Dict) -> float:
        """Calculate score based on customer relationship value"""
        base_score = 50  # Neutral starting point
        
        # Customer type adjustment
        customer_type = customer_info.get('customer_type', 'REGULAR')
        if customer_type == 'VIP':
            base_score -= 20  # Lower priority for collection to preserve relationship
        elif customer_type == 'HIGH_RISK':
            base_score += 30  # Higher priority for known risk customers
        elif customer_type == 'NEW':
            base_score += 10  # Moderate increase for new customers
        
        # Customer lifetime value
        lifetime_sales = customer_info.get('total_sales_lifetime', 0)
        if lifetime_sales >= self.value_tiers['tier_1_min']:
            base_score -= 15  # High value - handle with care
        elif lifetime_sales >= self.value_tiers['tier_2_min']:
            base_score -= 5   # Medium value - balanced approach
        elif lifetime_sales < self.value_tiers['tier_3_min']:
            base_score += 10  # Lower value - more aggressive collection
        
        # Credit limit utilization
        credit_limit = customer_info.get('credit_limit', 0)
        if credit_limit > 0:
            outstanding_total = 0
            self.cursor.execute("""
                SELECT SUM(outstanding_amount) FROM invoices 
                WHERE customer_id = ? AND outstanding_amount > 0
            """, (customer_id,))
            result = self.cursor.fetchone()
            if result and result[0]:
                outstanding_total = float(result[0])
                utilization = outstanding_total / credit_limit
                
                if utilization > 1.0:
                    base_score += 25  # Over credit limit
                elif utilization > 0.8:
                    base_score += 15  # High utilization
                elif utilization > 0.5:
                    base_score += 5   # Moderate utilization
        
        # Length of relationship
        customer_since = customer_info.get('customer_since')
        if customer_since:
            try:
                since_date = datetime.strptime(customer_since, '%Y-%m-%d').date()
                relationship_years = (datetime.now().date() - since_date).days / 365.25
                
                if relationship_years > 5:
                    base_score -= 10  # Long relationship - handle carefully
                elif relationship_years < 1:
                    base_score += 5   # New relationship - monitor closely
            except:
                pass  # Ignore date parsing errors
        
        return max(0, min(100, base_score))
    
    def _calculate_collection_effort_score(self, customer_id: int) -> float:
        """Calculate score based on previous collection efforts"""
        # Get recent collection activities
        self.cursor.execute("""
            SELECT COUNT(*) as total_activities,
                   COUNT(CASE WHEN activity_result = 'NO_ANSWER' THEN 1 END) as no_answer_count,
                   COUNT(CASE WHEN activity_result = 'PROMISE_MADE' THEN 1 END) as promise_count,
                   COUNT(CASE WHEN activity_result = 'DISPUTE_RAISED' THEN 1 END) as dispute_count,
                   MAX(activity_date) as last_activity_date
            FROM collection_activities
            WHERE customer_id = ? AND activity_date >= date('now', '-60 days')
        """, (customer_id,))
        
        result = self.cursor.fetchone()
        if not result or result[0] == 0:
            return 50  # No recent activity - neutral score
        
        total_activities, no_answer, promises, disputes, last_activity = result
        
        effort_score = 50  # Base score
        
        # Adjust based on contact success rate
        if total_activities > 0:
            no_answer_rate = no_answer / total_activities
            if no_answer_rate > 0.7:
                effort_score += 20  # Hard to reach - increase priority
            elif no_answer_rate < 0.3:
                effort_score -= 5   # Easy to reach - moderate priority
        
        # Adjust based on promises and disputes
        if promises > 0:
            effort_score += 10  # Customer making promises - monitor closely
        
        if disputes > 0:
            effort_score += 15  # Disputes require attention
        
        # Recent activity timing
        if last_activity:
            try:
                last_date = datetime.strptime(last_activity, '%Y-%m-%d').date()
                days_since_contact = (datetime.now().date() - last_date).days
                
                if days_since_contact > 14:
                    effort_score += 10  # No recent contact - increase priority
                elif days_since_contact < 3:
                    effort_score -= 5   # Very recent contact - can wait
            except:
                pass
        
        return max(0, min(100, effort_score))
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on priority score"""
        if score >= self.risk_thresholds['high_risk_score']:
            return "HIGH"
        elif score >= self.risk_thresholds['medium_risk_score']:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_recommendations(self, customer_id: int, customer_info: Dict, 
                                invoices: List[Dict], score: float, component_scores: Dict) -> List[str]:
        """Generate actionable recommendations based on scoring"""
        recommendations = []
        
        # Amount-based recommendations
        total_outstanding = sum(invoice['outstanding_amount'] for invoice in invoices)
        if total_outstanding > 50000:
            recommendations.append("High-value account: Consider personal attention from senior collector")
        elif total_outstanding < 500:
            recommendations.append("Low-value account: Consider automated collection only")
        
        # Aging-based recommendations
        oldest_days = max(invoice['days_past_due'] for invoice in invoices)
        if oldest_days > 90:
            recommendations.append("Critical aging: Escalate to collection manager immediately")
        elif oldest_days > 60:
            recommendations.append("Serious aging: Daily follow-up required")
        elif oldest_days > 30:
            recommendations.append("Standard follow-up: Weekly contact recommended")
        
        # History-based recommendations
        if component_scores['history'] < 30:
            recommendations.append("Poor payment history: Consider credit hold and COD terms")
        elif component_scores['history'] > 80:
            recommendations.append("Good payment history: Courteous approach, may just need reminder")
        
        # Relationship-based recommendations
        if customer_info.get('customer_type') == 'VIP':
            recommendations.append("VIP customer: Use diplomatic approach, consider senior staff involvement")
        elif customer_info.get('customer_type') == 'HIGH_RISK':
            recommendations.append("High-risk customer: Monitor closely, consider security/guarantees")
        
        # Effort-based recommendations
        if component_scores['effort'] > 70:
            recommendations.append("High collection effort required: Try different contact methods")
        
        # Overall score recommendations
        if score > 80:
            recommendations.append("URGENT: Immediate action required - consider legal consultation")
        elif score > 60:
            recommendations.append("HIGH PRIORITY: Daily monitoring and weekly contact")
        elif score < 30:
            recommendations.append("LOW PRIORITY: Standard automated collection process")
        
        # Credit hold recommendations
        if customer_info.get('is_credit_hold'):
            recommendations.append("Customer on credit hold: No new orders until balance resolved")
        
        # Promise tracking recommendations
        self.cursor.execute("""
            SELECT COUNT(*) FROM payment_promises 
            WHERE customer_id = ? AND status = 'ACTIVE'
        """, (customer_id,))
        active_promises = self.cursor.fetchone()[0]
        
        if active_promises > 0:
            recommendations.append(f"Active payment promises ({active_promises}): Monitor follow-up dates")
        
        return recommendations
    
    def _determine_next_action(self, score: float, oldest_days: int) -> str:
        """Determine the next recommended action"""
        if score > 80 or oldest_days > 120:
            return "ESCALATE_TO_LEGAL"
        elif score > 70 or oldest_days > 90:
            return "MANAGER_INTERVENTION"
        elif score > 60 or oldest_days > 60:
            return "IMMEDIATE_PHONE_CALL"
        elif score > 40 or oldest_days > 30:
            return "SEND_FORMAL_NOTICE"
        else:
            return "STANDARD_FOLLOW_UP"
    
    def get_prioritized_collection_queue(self, limit: int = 50, min_score: float = 30) -> List[Dict]:
        """Get prioritized list of customers for collection focus"""
        self.logger.info(f"Generating prioritized collection queue (limit: {limit}, min_score: {min_score})")
        
        # Get all customers with outstanding balances
        self.cursor.execute("""
            SELECT DISTINCT customer_id
            FROM invoices
            WHERE outstanding_amount > 0
        """)
        
        customer_ids = [row[0] for row in self.cursor.fetchall()]
        
        # Calculate scores for all customers
        prioritized_customers = []
        
        for customer_id in customer_ids:
            score_data = self.calculate_customer_priority_score(customer_id)
            
            if 'error' not in score_data and score_data['priority_score'] >= min_score:
                prioritized_customers.append(score_data)
        
        # Sort by priority score (descending)
        prioritized_customers.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Return top results
        return prioritized_customers[:limit]
    
    def update_customer_scores(self, customer_ids: List[int] = None) -> Dict:
        """Update and store priority scores for customers"""
        if customer_ids is None:
            # Get all customers with outstanding balances
            self.cursor.execute("""
                SELECT DISTINCT customer_id
                FROM invoices
                WHERE outstanding_amount > 0
            """)
            customer_ids = [row[0] for row in self.cursor.fetchall()]
        
        updated_count = 0
        errors = []
        
        for customer_id in customer_ids:
            try:
                score_data = self.calculate_customer_priority_score(customer_id)
                
                if 'error' not in score_data:
                    # Update customer record with new priority score
                    priority_level = "CRITICAL" if score_data['priority_score'] > 80 else \
                                   "HIGH" if score_data['priority_score'] > 60 else \
                                   "NORMAL" if score_data['priority_score'] > 30 else "LOW"
                    
                    self.cursor.execute("""
                        UPDATE customers
                        SET collection_priority = ?,
                            payment_reliability_score = ?,
                            updated_date = CURRENT_TIMESTAMP
                        WHERE customer_id = ?
                    """, (priority_level, min(100, score_data['priority_score']), customer_id))
                    
                    # Update invoice priority scores
                    self.cursor.execute("""
                        UPDATE invoices
                        SET collection_priority_score = ?,
                            updated_date = CURRENT_TIMESTAMP
                        WHERE customer_id = ? AND outstanding_amount > 0
                    """, (score_data['priority_score'], customer_id))
                    
                    updated_count += 1
                else:
                    errors.append(f"Customer {customer_id}: {score_data['error']}")
            
            except Exception as e:
                errors.append(f"Customer {customer_id}: {str(e)}")
        
        self.conn.commit()
        
        return {
            "updated_customers": updated_count,
            "total_requested": len(customer_ids),
            "errors": errors,
            "success_rate": updated_count / len(customer_ids) if customer_ids else 0
        }
    
    def generate_collection_focus_report(self) -> Dict:
        """Generate a report showing collection focus areas"""
        report = {
            "generated_date": datetime.now().isoformat(),
            "summary": {},
            "priority_segments": {},
            "aging_analysis": {},
            "customer_type_analysis": {},
            "recommendations": []
        }
        
        # Summary statistics
        self.cursor.execute("""
            SELECT 
                COUNT(DISTINCT customer_id) as total_customers,
                COUNT(*) as total_invoices,
                SUM(outstanding_amount) as total_outstanding,
                AVG(days_past_due) as avg_days_past_due,
                MAX(days_past_due) as max_days_past_due
            FROM invoices
            WHERE outstanding_amount > 0
        """)
        
        summary_data = self.cursor.fetchone()
        report["summary"] = {
            "total_customers_with_ar": summary_data[0],
            "total_outstanding_invoices": summary_data[1],
            "total_ar_balance": float(summary_data[2]),
            "average_days_past_due": round(float(summary_data[3]), 1),
            "oldest_invoice_days": summary_data[4]
        }
        
        # Priority segments
        priority_segments = ["CRITICAL", "HIGH", "NORMAL", "LOW"]
        for priority in priority_segments:
            self.cursor.execute("""
                SELECT 
                    COUNT(DISTINCT i.customer_id) as customer_count,
                    COUNT(*) as invoice_count,
                    SUM(i.outstanding_amount) as total_amount
                FROM invoices i
                JOIN customers c ON i.customer_id = c.customer_id
                WHERE i.outstanding_amount > 0 AND c.collection_priority = ?
            """, (priority,))
            
            data = self.cursor.fetchone()
            report["priority_segments"][priority] = {
                "customer_count": data[0] if data else 0,
                "invoice_count": data[1] if data else 0,
                "total_amount": float(data[2]) if data and data[2] else 0
            }
        
        # Aging analysis
        aging_buckets = ["CURRENT", "1-30", "31-60", "61-90", "91-120", "120+"]
        for bucket in aging_buckets:
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as invoice_count,
                    SUM(outstanding_amount) as total_amount
                FROM invoices
                WHERE outstanding_amount > 0 AND aging_bucket = ?
            """, (bucket,))
            
            data = self.cursor.fetchone()
            report["aging_analysis"][bucket] = {
                "invoice_count": data[0] if data else 0,
                "total_amount": float(data[1]) if data and data[1] else 0
            }
        
        # Customer type analysis
        customer_types = ["VIP", "REGULAR", "HIGH_RISK", "NEW"]
        for ctype in customer_types:
            self.cursor.execute("""
                SELECT 
                    COUNT(DISTINCT i.customer_id) as customer_count,
                    SUM(i.outstanding_amount) as total_amount,
                    AVG(i.days_past_due) as avg_days_past_due
                FROM invoices i
                JOIN customers c ON i.customer_id = c.customer_id
                WHERE i.outstanding_amount > 0 AND c.customer_type = ?
            """, (ctype,))
            
            data = self.cursor.fetchone()
            report["customer_type_analysis"][ctype] = {
                "customer_count": data[0] if data else 0,
                "total_amount": float(data[1]) if data and data[1] else 0,
                "avg_days_past_due": round(float(data[2]), 1) if data and data[2] else 0
            }
        
        # Generate recommendations based on analysis
        total_ar = report["summary"]["total_ar_balance"]
        critical_amount = report["priority_segments"]["CRITICAL"]["total_amount"]
        high_amount = report["priority_segments"]["HIGH"]["total_amount"]
        
        if critical_amount > total_ar * 0.3:
            report["recommendations"].append("High concentration of critical accounts - consider immediate intervention")
        
        if report["aging_analysis"]["120+"]["total_amount"] > total_ar * 0.15:
            report["recommendations"].append("Significant aged receivables - review write-off policies")
        
        if report["customer_type_analysis"]["HIGH_RISK"]["total_amount"] > total_ar * 0.25:
            report["recommendations"].append("High exposure to risky customers - review credit policies")
        
        return report
    
    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == "__main__":
    # Example usage
    prioritizer = CollectionPrioritizer()
    try:
        # Generate prioritized queue
        queue = prioritizer.get_prioritized_collection_queue(20)
        print(f"Top 20 priority customers:")
        for i, customer in enumerate(queue[:10], 1):
            print(f"{i}. {customer['customer_name']} - Score: {customer['priority_score']} - ${customer['total_outstanding']:,.2f}")
        
        # Generate focus report
        report = prioritizer.generate_collection_focus_report()
        print(f"\nTotal AR Balance: ${report['summary']['total_ar_balance']:,.2f}")
        print(f"Average Days Past Due: {report['summary']['average_days_past_due']}")
        
    finally:
        prioritizer.close()