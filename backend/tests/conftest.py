import os

# CI / local pytest without Mongo: LangGraph MemorySaver (see graph.checkpointer).
os.environ.setdefault("CONSILIUM_CHECKPOINTER", "memory")
