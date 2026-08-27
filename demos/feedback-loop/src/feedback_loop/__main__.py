"""Enable ``python -m feedback_loop``.

Convention: the ``__main__`` module is a thin shim that delegates to
``main.main()``.  It contains no CLI dispatch logic — all routing
happens through the web layer.
"""

from __future__ import annotations

import sys

from feedback_loop.main import main

sys.exit(main())
