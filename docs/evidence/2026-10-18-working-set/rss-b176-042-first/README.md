# First 32-generation RSS matrix on b176/042

This preserves the first long-run matrix, including its failure. It uses
immutable Observer b176ac06 and Mesh 042fe3a5, with cyclic GC disabled and no
explicit collection. The runner performs one ordinary watch and four detached
local reads per generation. It is an untimed synthetic component screen.

All 32 generations in each completed case passed functional admission, fresh
proof and DTO checks. The four 500-row cases retired all six owner weakrefs.
The Python 3.14 full-feed 2,000-row case retained its Bridge after shutdown;
the Runtime, state, Reader and all Client weakrefs retired. The controller
stopped there, leaving the remaining three planned cases unexecuted.

After local copies were released, the last sixteen full-feed 2,000-row RSS
samples rose from 274,845,696 to 372,314,112 bytes. The corresponding full-feed
500-row tails also rose on both interpreters. Source encoded-body accounting
remained bounded and every recorded encoded equation reconciled. Those facts
do not establish which physical objects account for the RSS rise, or prove
that allocator retention is the cause.

This is a failed lifetime/plateau checkpoint, not a safe memory bound or
performance result. `matrix-result.json`, individual reports, original logs,
the declared eight-case plan and both runner files are byte-preserved here.
`receipt.json` hashes those files. Any later diagnostic or correction gets its
own source tuple and outputs. The earlier short-run lifetime checks and private
installed-package checks retain their narrower scope.
