"""ORCHID-SAGE MCP server: machine-executable CALPHAD protocols (read, check, plan, run, compare, modify).

Two modes on one set of documents (protocols/, orchid-assessment-schema@1.0.0-draft):
  reproduce  an existing specific protocol (e.g. crni-paper-fit-step4-s1@0.1.0-draft): stage by hash, run, compare;
  fresh      a new assessment instantiated from the general protocol orchid-calphad-fit@2.0.0 in its own run root.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
