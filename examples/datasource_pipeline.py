"""Example: DataSource + StreamingIngestion pipeline.

Demonstrates how to wire an EastMoneyAdapter into the streaming pipeline
for real-time stock data collection.

Usage::

    python examples/datasource_pipeline.py
"""

from __future__ import annotations

from synapse.event.adapters import EastMoneyAdapter, adapter_fetch_fn
from synapse.event.streaming import PollingSource, StreamingIngestion


def main() -> None:
    # 1. Create adapter
    adapter = EastMoneyAdapter()

    # 2. Create streaming ingestion with adapter as fetch function
    ingestion = StreamingIngestion(buffer_size=500)
    ingestion.set_fetch_fn(adapter_fetch_fn(adapter))

    # 3. Register polling source with target tickers
    ingestion.register_source(PollingSource(
        source_id="eastmoney_realtime",
        name="eastmoney_realtime_quotes",
        url="http://push2.eastmoney.com/api/qt/ulist.np/get",
        poll_interval_sec=60,
        params={"tickers": "600519,000001,300750"},
    ))

    # 4. Single poll (for demo; production would use start())
    results = ingestion.poll_once()
    print(f"Fetched {len(results)} records")
    for r in results[:3]:
        print(f"  {r.get('ticker')}: {r.get('payload', {}).get('price', 'N/A')}")


if __name__ == "__main__":
    main()
