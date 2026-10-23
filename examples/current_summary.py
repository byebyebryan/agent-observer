"""Developer JSON projection using the installed public utility reader."""

from agent_observer.utility_read import local_failure_code as local_failure_code
from agent_observer.utility_read import local_summary as local_summary
from agent_observer.utility_read import main as main
from agent_observer.utility_read import parser as parser
from agent_observer.utility_read import run_local as run_local
from agent_observer.utility_read import run_mesh as run_mesh
from agent_observer.utility_read import ticked as ticked

if __name__ == "__main__":
    raise SystemExit(main())
