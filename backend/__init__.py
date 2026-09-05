"""Durable multi-user application services.

The Streamlit interface is intentionally not imported here. These modules own
identity, public archive records and long-running task state so a browser rerun
or a UI-process restart cannot lose accepted work.
"""
