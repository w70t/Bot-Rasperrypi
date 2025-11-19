"""
Analytics Service - Business Metrics and Analytics
Calculates KPIs, revenue forecasts, and user analytics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.services.auth_service import auth_service
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Analytics Service for business intelligence
    """

    async def calculate_mrr(self) -> float:
        """
        Calculate Monthly Recurring Revenue

        Returns:
            MRR in USD
        """
        try:
            basic_users = await auth_service.get_user_count(plan="basic", status="active")
            pro_users = await auth_service.get_user_count(plan="pro", status="active")
            business_users = await auth_service.get_user_count(plan="business", status="active")

            mrr = (
                basic_users * settings.PRICE_BASIC +
                pro_users * settings.PRICE_PRO +
                business_users * settings.PRICE_BUSINESS
            )

            return round(mrr, 2)

        except Exception as e:
            logger.error(f"Error calculating MRR: {str(e)}")
            return 0.0

    async def calculate_arr(self) -> float:
        """
        Calculate Annual Recurring Revenue

        Returns:
            ARR in USD
        """
        mrr = await self.calculate_mrr()
        return round(mrr * 12, 2)

    async def calculate_churn_rate(self, period_days: int = 30) -> float:
        """
        Calculate churn rate

        Args:
            period_days: Period to calculate churn over

        Returns:
            Churn rate as percentage
        """
        try:
            from app.database import Collections

            # Get users at start of period
            period_start = datetime.utcnow() - timedelta(days=period_days)

            # Count users who were active at start of period
            active_at_start = await Collections.users().count_documents({
                "created_at": {"$lte": period_start},
                "status": {"$in": ["active", "cancelled"]}  # Both active and cancelled at that time
            })

            if active_at_start == 0:
                return 0.0

            # Count users who cancelled during the period
            cancelled_during_period = await Collections.users().count_documents({
                "status": "cancelled",
                "updated_at": {"$gte": period_start},
                "created_at": {"$lte": period_start}
            })

            # Calculate churn rate
            churn_rate = (cancelled_during_period / active_at_start) * 100

            logger.info(f"Churn rate ({period_days}d): {churn_rate:.2f}% ({cancelled_during_period}/{active_at_start})")
            return round(churn_rate, 2)

        except Exception as e:
            logger.error(f"Error calculating churn rate: {str(e)}")
            return 0.0

    async def calculate_conversion_rate(self) -> float:
        """
        Calculate Free to Paid conversion rate

        Returns:
            Conversion rate as percentage
        """
        try:
            total_users = await auth_service.get_user_count()
            free_users = await auth_service.get_user_count(plan="free")
            paid_users = total_users - free_users

            if total_users == 0:
                return 0.0

            conversion_rate = (paid_users / total_users) * 100
            return round(conversion_rate, 2)

        except Exception as e:
            logger.error(f"Error calculating conversion rate: {str(e)}")
            return 0.0

    async def get_revenue_forecast(self, months: int = 3) -> List[Dict]:
        """
        Forecast revenue for next N months

        Args:
            months: Number of months to forecast

        Returns:
            List of revenue forecasts
        """
        try:
            current_mrr = await self.calculate_mrr()

            # Simple linear growth forecast (10% monthly growth)
            growth_rate = 1.10
            forecasts = []

            for i in range(1, months + 1):
                forecast_date = datetime.utcnow() + timedelta(days=30 * i)
                forecast_mrr = current_mrr * (growth_rate ** i)

                forecasts.append({
                    'month': forecast_date.strftime('%Y-%m'),
                    'mrr': round(forecast_mrr, 2),
                    'growth_rate': '10%'
                })

            return forecasts

        except Exception as e:
            logger.error(f"Error forecasting revenue: {str(e)}")
            return []

    async def get_user_cohorts(self) -> Dict:
        """
        Analyze user cohorts by signup month

        Returns:
            Cohort analysis data
        """
        try:
            from app.database import Collections

            # Aggregate users by signup month
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "year": {"$year": "$created_at"},
                            "month": {"$month": "$created_at"}
                        },
                        "total_users": {"$sum": 1},
                        "active_users": {
                            "$sum": {"$cond": [{"$eq": ["$status", "active"]}, 1, 0]}
                        },
                        "cancelled_users": {
                            "$sum": {"$cond": [{"$eq": ["$status", "cancelled"]}, 1, 0]}
                        },
                        "avg_requests": {"$avg": "$requests_used"}
                    }
                },
                {
                    "$sort": {"_id.year": -1, "_id.month": -1}
                },
                {
                    "$limit": 12  # Last 12 months
                }
            ]

            cohorts_cursor = Collections.users().aggregate(pipeline)
            cohorts_list = await cohorts_cursor.to_list(length=12)

            # Format results
            cohorts = {}
            for cohort in cohorts_list:
                month_key = f"{cohort['_id']['year']}-{cohort['_id']['month']:02d}"
                retention_rate = (cohort['active_users'] / cohort['total_users'] * 100) if cohort['total_users'] > 0 else 0

                cohorts[month_key] = {
                    "total_users": cohort['total_users'],
                    "active_users": cohort['active_users'],
                    "cancelled_users": cohort['cancelled_users'],
                    "retention_rate": round(retention_rate, 2),
                    "avg_requests": round(cohort['avg_requests'], 2) if cohort['avg_requests'] else 0
                }

            logger.info(f"Analyzed {len(cohorts)} cohorts")
            return cohorts

        except Exception as e:
            logger.error(f"Error analyzing cohorts: {str(e)}")
            return {}

    async def get_top_users(self, limit: int = 10) -> List[Dict]:
        """
        Get top users by API usage

        Args:
            limit: Number of users to return

        Returns:
            List of top users
        """
        try:
            from app.database import Collections

            # Query users sorted by requests_used, descending
            cursor = Collections.users().find(
                {"status": "active"},  # Only active users
                {
                    "email": 1,
                    "plan": 1,
                    "requests_used": 1,
                    "requests_limit": 1,
                    "last_request_at": 1,
                    "_id": 0
                }
            ).sort("requests_used", -1).limit(limit)

            top_users = await cursor.to_list(length=limit)

            # Format results
            formatted_users = []
            for user in top_users:
                usage_percent = (user['requests_used'] / user['requests_limit'] * 100) if user['requests_limit'] > 0 else 0

                formatted_users.append({
                    "email": user['email'],
                    "plan": user['plan'],
                    "requests_used": user['requests_used'],
                    "requests_limit": user['requests_limit'],
                    "usage_percent": round(usage_percent, 2),
                    "last_request_at": user.get('last_request_at')
                })

            logger.info(f"Retrieved top {len(formatted_users)} users")
            return formatted_users

        except Exception as e:
            logger.error(f"Error getting top users: {str(e)}")
            return []

    async def get_usage_patterns(self) -> Dict:
        """
        Analyze API usage patterns

        Returns:
            Usage patterns (peak hours, days, etc.)
        """
        try:
            from app.database import Collections

            # Analyze usage data from last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            # Aggregate by hour of day
            hour_pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": thirty_days_ago}
                    }
                },
                {
                    "$group": {
                        "_id": {"$hour": "$timestamp"},
                        "count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"count": -1}
                }
            ]

            # Aggregate by day of week
            day_pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": thirty_days_ago}
                    }
                },
                {
                    "$group": {
                        "_id": {"$dayOfWeek": "$timestamp"},
                        "count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"count": -1}
                }
            ]

            # Get total requests
            total_requests = await Collections.usage().count_documents({
                "timestamp": {"$gte": thirty_days_ago}
            })

            # Execute aggregations
            hour_cursor = Collections.usage().aggregate(hour_pipeline)
            hour_results = await hour_cursor.to_list(length=24)

            day_cursor = Collections.usage().aggregate(day_pipeline)
            day_results = await day_cursor.to_list(length=7)

            # Determine peak hour
            peak_hour = 14  # Default
            if hour_results:
                peak_hour = hour_results[0]['_id']

            # Determine peak day
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            peak_day = 'Wednesday'  # Default
            if day_results:
                peak_day_num = day_results[0]['_id']
                peak_day = day_names[peak_day_num - 1] if 1 <= peak_day_num <= 7 else 'Wednesday'

            # Calculate average requests per hour
            hours_in_period = 30 * 24  # 30 days
            avg_requests_per_hour = round(total_requests / hours_in_period, 2) if hours_in_period > 0 else 0

            # Build hourly distribution
            hourly_distribution = {}
            for result in hour_results:
                hourly_distribution[result['_id']] = result['count']

            # Build daily distribution
            daily_distribution = {}
            for result in day_results:
                day_num = result['_id']
                if 1 <= day_num <= 7:
                    daily_distribution[day_names[day_num - 1]] = result['count']

            patterns = {
                'peak_hour': f'{peak_hour:02d}:00-{peak_hour+1:02d}:00',
                'peak_day': peak_day,
                'avg_requests_per_hour': avg_requests_per_hour,
                'total_requests_30d': total_requests,
                'busiest_endpoint': '/api/v1/video/extract',  # Primary endpoint
                'hourly_distribution': hourly_distribution,
                'daily_distribution': daily_distribution
            }

            logger.info(f"Usage patterns: Peak {peak_day} at {peak_hour}:00, Avg {avg_requests_per_hour}/hr")
            return patterns

        except Exception as e:
            logger.error(f"Error analyzing usage patterns: {str(e)}")
            # Return safe defaults on error
            return {
                'peak_hour': '14:00-15:00',
                'peak_day': 'Wednesday',
                'avg_requests_per_hour': 0,
                'total_requests_30d': 0,
                'busiest_endpoint': '/api/v1/video/extract',
                'hourly_distribution': {},
                'daily_distribution': {}
            }

    async def get_plan_distribution(self) -> Dict[str, int]:
        """
        Get distribution of users across plans

        Returns:
            Dictionary of plan counts
        """
        try:
            distribution = {
                'free': await auth_service.get_user_count(plan="free"),
                'basic': await auth_service.get_user_count(plan="basic"),
                'pro': await auth_service.get_user_count(plan="pro"),
                'business': await auth_service.get_user_count(plan="business")
            }

            return distribution

        except Exception as e:
            logger.error(f"Error getting plan distribution: {str(e)}")
            return {}

    async def get_ltv(self, plan: str) -> float:
        """
        Calculate Customer Lifetime Value for a plan

        Args:
            plan: Plan name

        Returns:
            LTV in USD
        """
        try:
            # Simplified LTV calculation:
            # LTV = Average Revenue Per User * Average Lifetime (months)

            plan_prices = {
                'basic': settings.PRICE_BASIC,
                'pro': settings.PRICE_PRO,
                'business': settings.PRICE_BUSINESS
            }

            price = plan_prices.get(plan, 0)

            # Assume average lifetime of 12 months (placeholder)
            avg_lifetime_months = 12

            ltv = price * avg_lifetime_months

            return round(ltv, 2)

        except Exception as e:
            logger.error(f"Error calculating LTV: {str(e)}")
            return 0.0


# Singleton instance
analytics_service = AnalyticsService()
