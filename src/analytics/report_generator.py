"""Weekly report generator — creates performance reports for Notion and Discord."""

import json
import os
from datetime import datetime

from src.analytics.collector import get_analytics_summary, update_content_weights

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def generate_weekly_report():
    """Generate the weekly performance report.

    Called automatically every Monday. Creates a report dict that gets
    published to Notion and summarized in Discord #weekly-analytics.

    Returns:
        Report dict with all analytics data.
    """
    summary = get_analytics_summary()
    weights = update_content_weights()

    # Load character data for names
    with open(os.path.join(DATA_DIR, "characters.json"), "r") as f:
        characters = json.load(f)["characters"]

    # Build character rankings from weights
    char_weights = weights.get("character_weights", {})
    char_rankings = sorted(
        [(cid, char_weights.get(cid, 1.0)) for cid in characters],
        key=lambda x: x[1],
        reverse=True,
    )

    report = {
        "report_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "period": "Weekly",
        "summary": {
            "total_episodes": summary["total_episodes"],
            "total_views": summary["total_views"],
            "total_likes": summary["total_likes"],
            "total_comments": summary["total_comments"],
            "total_shares": summary["total_shares"],
        },
        "top_episodes": {
            "by_views": summary["top_episodes_by_views"],
            "by_engagement": summary["top_episodes_by_engagement"],
        },
        "character_rankings": [
            {
                "character": cid,
                "name": characters[cid]["nickname"],
                "weight": weight,
            }
            for cid, weight in char_rankings
        ],
        "platform_breakdown": summary["platform_breakdown"],
        "weight_adjustments": {
            "character_weights": weights.get("character_weights", {}),
            "situation_weights": weights.get("situation_weights", {}),
            "punchline_weights": weights.get("punchline_weights", {}),
            "location_weights": weights.get("location_weights", {}),
        },
        "recommendations": _generate_recommendations(summary, weights),
    }

    return report


def _generate_recommendations(summary, weights):
    """Generate simple recommendations based on analytics data.

    Args:
        summary: Analytics summary dict.
        weights: Current content weights.

    Returns:
        List of recommendation strings.
    """
    recommendations = []

    if summary["total_episodes"] == 0:
        recommendations.append("No episodes published yet. Start generating content!")
        return recommendations

    if summary["total_views"] == 0:
        recommendations.append("No view data available yet. Platform APIs need to be connected for analytics.")
        return recommendations

    # Check for underperforming characters
    char_weights = weights.get("character_weights", {})
    low_chars = [cid for cid, w in char_weights.items() if w < 0.8]
    if low_chars:
        recommendations.append(
            f"Consider pairing underperforming characters ({', '.join(low_chars)}) "
            f"with top performers for better engagement."
        )

    # Check platform balance
    breakdown = summary.get("platform_breakdown", {})
    platform_views = {p: d.get("views", 0) for p, d in breakdown.items()}
    if platform_views:
        max_platform = max(platform_views, key=platform_views.get)
        min_platform = min(platform_views, key=platform_views.get)
        if platform_views[max_platform] > 0 and platform_views[min_platform] == 0:
            recommendations.append(
                f"{min_platform.capitalize()} has no views. Check if publishing is working correctly."
            )

    if not recommendations:
        recommendations.append("All metrics look healthy. Keep up the current content mix!")

    return recommendations


def format_discord_summary(report):
    """Format a concise weekly summary for the Discord #weekly-analytics channel.

    Args:
        report: Full report dict from generate_weekly_report().

    Returns:
        Formatted message string.
    """
    s = report.get("summary", {})
    lines = [
        f"**Weekly Analytics Report — {report.get('report_date', 'N/A')}**\n",
        f"Episodes: {s.get('total_episodes', 0)}",
        f"Total Views: {s.get('total_views', 0):,}",
        f"Likes: {s.get('total_likes', 0):,} | Comments: {s.get('total_comments', 0):,} | Shares: {s.get('total_shares', 0):,}\n",
    ]

    # Top episodes
    top_views = report.get("top_episodes", {}).get("by_views", [])
    if top_views:
        lines.append("**Top Episodes by Views:**")
        for i, ep in enumerate(top_views[:3]):
            lines.append(f"  {i+1}. {ep['episode_id']} — {ep['views']:,} views")
        lines.append("")

    # Character rankings
    rankings = report.get("character_rankings", [])
    if rankings:
        lines.append("**Character Rankings:**")
        for r in rankings:
            bar = "+" if r["weight"] > 1.0 else "-" if r["weight"] < 1.0 else "="
            lines.append(f"  {r['name']}: {r['weight']:.2f} [{bar}]")
        lines.append("")

    # Recommendations
    recs = report.get("recommendations", [])
    if recs:
        lines.append("**Recommendations:**")
        for rec in recs:
            lines.append(f"  - {rec}")

    return "\n".join(lines)
