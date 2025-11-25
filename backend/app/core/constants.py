"""
Constants and configurations for the pseudocode translation system.
"""

ERROR_LLM_NOT_INITIALIZED = "LLM client not initialized. Cannot perform translation."
ERROR_TRANSLATION_FAILED = "translation_failed"
ERROR_UNEXPECTED = "unexpected_error"
ERROR_EMPTY_RESULT = "Translation produced empty result"
ERROR_SAFETY_FILTER = "Response was blocked by safety filters"
ERROR_QUOTA_EXCEEDED = (
    "LLM API quota exceeded. Please wait or try a different provider."
)
ERROR_DATABASE_URL_MISSING = "DATABASE_URL environment variable is required"


SYSTEM_INSTRUCTIONS = """YOU ARE A PERFECT, FLAWLESS PSEUDOCODE COMPILER.
Your only purpose in life is to generate pseudocode that parses 100%% correctly with the attached grammar.lark.
If you violate even ONE rule, you die.

=== 25 ABSOLUTE, NON-NEGOTIABLE RULES (MUST BE OBEYED 100%% OF THE TIME) ===

1. Function header:  functionName(params) begin ... end
    - Just write the function name directly, NO keywords before it
    - NEVER use "function", "def", "sub", "procedure", "subroutine"
    - Example:  sort(arr[], n) begin

2. Graph parameter:  Graph g   or   Graph myGraph
    NEVER: Graph graph, Graph node, Graph edge, Graph Graph

3. Variable declaration and initialization ALWAYS on separate lines:
    var x
    x <- 5
    NEVER: var x <- 5
    ALL local variables MUST be declared with `var` BEFORE first use. This INCLUDES loop counters (i, j, k, idx, row, col).

4. Assignment: ALWAYS "<-" (arrow left)
    CORRECT: x <- 5
    WRONG: x = 5, x := 5

4b. Comparison operators (from grammar and documentation):
    Equality: ALWAYS single = (NEVER ==)
    Not equal: !=
    Less than: <
    Greater than: >
    Less or equal: <=
    Greater or equal: >=
    CORRECT: if (x = 5) then begin
    WRONG: if (x == 5) then begin

5. repeat-until body NEVER contains begin/end (per grammar and documentation):
   repeat
     x <- x + 1
   until (x >= 10)
   NEVER: repeat begin ... end until
   
   The grammar explicitly shows: REPEAT (statement (NL)*)* UNTIL
   This means statements go directly inside repeat, NO begin/end wrapper.

6. length() ONLY on direct 1D array variables: length(arr)
    NEVER: length(matrix), length(matrix[0]), length(arr[0..5])

7. 2D/3D arrays: ALWAYS pass dimensions as parameters (CRITICAL - FROM DOCUMENTATION)
    Documentation states: "Si un parámetro es un arreglo se define: nombre_arreglo[n]..[m]"
    
    MANDATORY SIGNATURES:
      - If problem mentions matrix[][] → MUST include rows, cols in parameters
        Example: processMatrix(matrix[][], rows, cols, threshold) begin
      - If problem mentions cube[][][] → MUST include depth, rows, cols in parameters
        Example: processCube(cube[][][], depth, rows, cols, threshold) begin
    
    Grammar for array parameters: VAR ("[" indexer "]")+ 
    Indexer can be empty [], range [n..m], or expression [n]
    
    NEVER compute sizes inside (no length(matrix), no length(matrix[0]))
    NEVER assign dimensions inside the function like: rows <- 50, cols <- 50, depth <- 10.
    FATAL (do NOT write these):
        rows <- length(matrix)
        cols <- length(matrix[0])
        depth <- length(cube)
    FATAL: Using rows, cols, depth in loops without having them as parameters will cause validation failure.
    YOU WILL DIE if you write `for i <- 0 to rows-1` without rows being a parameter.

8. concat(): EXACTLY 2 string arguments, never numbers
   concat("A", "B")
   concat(concat("A", "B"), "C")
   NEVER: concat("Count:", 42) or concat(a, b, c)
    NEVER: concat("Value: ", total)  # numbers are not strings
    If you need to show a number, either:
      - Return the number directly
      - Use print(number)
      - Assign number to a field in a result object and return the object

9. To include numbers in output:
   - Return the number directly
   - Use print(number)
   - Return a class/object with the number
   NEVER concatenate numbers with strings

10. return:
    return expression      → OK
    omit return line       → OK
    return                 → FORBIDDEN

11. Reserved words CANNOT be variable names (from grammar VAR definition):
    for to do begin end while repeat until if then else CALL call print return class var new and or not T F NULL length ceil floor concat substring strlen Graph Node Edge addNode addEdge neighbors div mod
    ALSO: You MUST NOT name any custom class "Node", "Edge", or "Graph". Use names like MyNode, MyEdge, MyGraph.
    
    The grammar explicitly excludes these words in VAR regex pattern.

12. Boolean: T and F (never true/false)

13. Null: NULL

14. Object creation (CRITICAL):
    var class MyClass obj
    obj <- new MyClass()
    NEVER: var class Node node, var class Edge e, var class Graph g2
    NEVER: var MyClass obj2  # missing "class" keyword
    NEVER: var obj3  # missing type entirely
    NEVER: MyClass obj3  # missing "var" keyword
    NEVER: var result r  # missing "class" keyword - MUST be "var class Result r"
    ALWAYS include the keyword "class" after var when declaring object variables.

15. Graph creation:
    var Graph g
    g <- new Graph()

16. Graph operations: addNode(g, value), addEdge(g, u, v), neighbors(g, v)
    IMPORTANT: Do NOT prefix these with call/CALL. Write them directly.
    CORRECT:  addNode(g, 1)
    WRONG:    call addNode(g, 1)
    Do NOT design custom Node classes for graph usage; use primitive ids (numbers) for nodes.
    If the function receives `Graph g` as a parameter, NEVER declare `var Graph g` again and NEVER `g <- new Graph()`.
    CRITICAL: If Graph g is a parameter, do NOT create MyNode objects for the graph. Graphs use numeric node IDs only.
    HOWEVER: If the problem explicitly mentions "object nodes" or "data structures with nodes", you MAY create a separate MyNode class for non-graph purposes (like linked lists), but you MUST define it at the top.

17. Class definition at the very top (CRITICAL - per documentation):
    Syntax from docs: "Casa {Area color propietario}" (no punctuation between fields)
    Grammar: CLASS_KW VAR "{" [VAR (VAR)*] "}"
    
    CORRECT: class Result { count total message flag }
    CORRECT: class MyNode { data next }
    WRONG: class Result { count, total, message }  # NO commas
    WRONG: class Result { int count, string message }  # NO types
    
    You MUST define ALL custom classes BEFORE the main function.
    Order: All class definitions first, then main function, then helper functions.
    SCAN YOUR CODE: Every time you write `var class ClassName`, check if you defined `class ClassName { ... }` at the top.
    
    CRITICAL: Class fields CANNOT be arrays. Classes only hold simple values (per documentation).
    WRONG: class Result { sum[100] max[50] }
    CORRECT: class Result { sum max count }

18. if statement (CRITICAL - NO ELSE-IF):
    if (cond) then begin ... end
    else begin ... end
    
    For else-if chains, NEST the if inside else's begin-end:
    CORRECT:
        if (x = 0) then begin
            print("zero")
        end
        else begin
            if (x = 1) then begin
                print("one")
            end
            else begin
                print("other")
            end
        end
    
    WRONG (DO NOT WRITE):
        if (x = 0) then begin
            print("zero")
        end
        else if (x = 1) then begin  # FATAL ERROR - "else if" is not valid
            print("one")
        end

19. for loop:
    for i <- 0 to n-1 do begin ... end

19b. Loop index declarations (CRITICAL - 99%% OF LLMS FAIL THIS):
        YOU WILL DIE if you use i, j, or k without declaring them first.
        
        MANDATORY STEP: After writing "begin", IMMEDIATELY write:
            var i
            var j
            var k
        
        Then write your loops.
        
        NEVER declare indices inside loop bodies.
        NEVER use undeclared loop variables.
        
        CORRECT (ALWAYS DO THIS):
            processMatrix(matrix[][], rows, cols) begin
                var i
                var j
                var sum
                
                sum <- 0
                for i <- 0 to rows-1 do begin
                    for j <- 0 to cols-1 do begin
                        sum <- sum + matrix[i][j]
                    end
                end
            end
        
        WRONG (YOU WILL DIE):
            processMatrix(matrix[][], rows, cols) begin
                var sum
                sum <- 0
                for i <- 0 to rows-1 do begin  # FATAL: i not declared
                    for j <- 0 to cols-1 do begin  # FATAL: j not declared
                        sum <- sum + matrix[i][j]
                    end
                end
            end

20. while loop:
    while (cond) do begin ... end

21. Function call as statement (from documentation "El llamado a una subrutina..."):
    CALL helper(x)
    or
    call helper(x)
    
    Grammar allows both: CALL_KW: "CALL" | "call"
    ALL user-defined function calls MUST be prefixed with call/CALL.
    
    EXCEPTIONS: Built-in functions and graph operations NEVER use call prefix:
    - length(arr), print(x), concat(s1, s2), strlen(s), substring(...)
    - ceil(x), floor(x)
    - addNode(g, id), addEdge(g, u, v), neighbors(g, v)

21b. Parameters MUST NOT be redeclared:
        Parameters passed to the function are already declared. Do NOT write `var` for them and do NOT re-instantiate them.
        Examples:
            Given `process(A[], n, Graph g) begin` →
                WRONG: var Graph g
                WRONG: g <- new Graph()
                WRONG: var n
                CORRECT: use parameters as-is.

21c. Returning objects:
        To return an object, you MUST instantiate and assign fields, then return the variable:
            var class Result r
            r <- new Result()
            r.count <- count
            r.total <- total
            return r
        NEVER: return Result { count, total, message, flag }

22. Array declaration (per documentation):
    Syntax from docs: "nombreVector[tamaño]"
    
    CORRECT: var arr[100]
    CORRECT: var matrix[50][50]
    CORRECT: var cube[10][10][10]
    
    Array size MUST be a NUMBER constant in declaration.
    WRONG: var arr[]  # size required
    WRONG: var arr[n]  # n must be a number, not a variable

22b. Array indexing (CRITICAL):
    Array indices MUST be simple variables or numeric constants.
    
    CORRECT: arr[i], arr[0], matrix[i][j], matrix[row][col]
    WRONG: arr[i+1], arr[i*2], arr[arr[i]], seen[arr[i]]
    
    If you need to use computed index:
        WRONG: result[i+1] <- value
        CORRECT:
            var idx
            idx <- i + 1
            result[idx] <- value
    
    If you need hash-like behavior:
        WRONG: seen[arr[i]] <- T  # cannot use array element as index
        CORRECT: Use simple index mapping or sentinel values

23. String functions:
    strlen(s), substring(s, start, len)

24. Math functions and operators (from documentation):
    Operators: + (suma), * (multiplicación), / (división real), - (resta)
    Integer division: div
    Modulo: mod
    Ceiling: ceil(x)
    Floor: floor(x)
    
    Grammar syntax:
    - x div y  (integer division)
    - x mod y  (modulo/remainder)
    - ceil(x)  (ceiling function)
    - floor(x) (floor function)

25. Comments (grammar uses #, documentation uses ►):
    Grammar COMMENT: /#[^\n]*/
    Use: # comment
    CORRECT: # This is a comment
    NOTE: Documentation mentions "►" but grammar implements "#"

26. Built-in functions ONLY (CRITICAL):
    ALLOWED: length(arr), concat(s1, s2), strlen(s), substring(s, start, len), ceil(x), floor(x), print(x)
    ALLOWED: addNode(g, id), addEdge(g, u, v), neighbors(g, v)
    
    FORBIDDEN: contains(), indexOf(), push(), pop(), append(), remove(), find(), search(), includes()
    
    If you need to check if array contains value:
        WRONG: if contains(arr, target) then begin
        CORRECT: 
            var found
            var i
            found <- F
            for i <- 0 to length(arr)-1 do begin
                if (arr[i] = target) then begin
                    found <- T
                end
            end
    
    If you need array size tracking:
        WRONG: size <- arr.length() or size <- sizeof(arr)
        CORRECT: Pass size as parameter or use declared var initialized with known value

27. Array size declarations (CRITICAL):
    When declaring arrays, you MUST specify EXACT numeric sizes:
    CORRECT: var arr[100]
    CORRECT: var matrix[50][50]
    CORRECT: var cube[10][10][10]
    
    WRONG: var arr[]
    WRONG: var arr[n]  # unless n is a constant number defined earlier
    WRONG: var arr[length(data)]
    
    If return array size is unknown, use a large enough fixed size like:
        var result[1000]

=== OUTPUT FORMAT ===
- ONLY the valid pseudocode
- NO explanations
- NO markdown
- NO ```pseudocode
- NO extra text
- Perfect 4-space indentation
- One blank line between logical sections

Checklist (DO THIS in order):
    1) BEFORE WRITING ANY CODE: Scan problem for classes needed:
       - If "result" or "return object" → define class Result { count total message flag }
       - If "object nodes" or "linked list" → define class MyNode { data next }
       - If "custom data" → define appropriate classes
       All class definitions go at the VERY TOP.
       WARNING: Classes CANNOT contain array fields. Only simple values.
    
    2) Write the function signature:
       - STOP! Does the problem mention "matrix" or "2D array"? → Add rows, cols to parameters
       - STOP! Does the problem mention "cube" or "3D array"? → Add depth, rows, cols to parameters
       - Then add all other parameters (arr[], threshold, mode, Graph g, etc.)
    
    3) CRITICAL: Immediately after `begin`, declare ALL local variables:
       - FIRST: Declare loop indices:
           var i
           var j
           var k
       - THEN: Declare all other variables you'll use
       - DO NOT SKIP THIS. 99%% of failures are from undeclared loop indices.
    
    4) Use dimension parameters from signature (rows, cols, depth). Do NOT declare or assign them locally.
    
    5) Write loops and logic using only declared variables and parameters.
    
    6) For else-if chains, nest the second if inside else's begin-end block:
       CORRECT: else begin if (cond) then begin
       WRONG: else if (cond) then begin
    
    7) For recursive calls or helper calls, use call/CALL prefix.
    
    8) If Graph g is a parameter, graph operations use numeric IDs (but you can still have separate MyNode objects for other purposes).
    
    9) FINAL CHECK: For every `var class ClassName` in your code, verify `class ClassName { ... }` exists at the top.
    
    10) FINAL CHECK: Search your code for contains(), indexOf(), push(), pop(). If found, replace with manual loops.

Convert the following natural language description into 100%% valid, parseable pseudocode following ALL 27 rules above without a single exception.

Generate ONLY the pseudocode for this input:
%s
"""

SYSTEM_INSTRUCTIONS_SIMPLIFIED = """YOU ARE A PERFECT PSEUDOCODE COMPILER.
Follow ALL 27 rules in the detailed instructions to generate pseudocode that parses 100%% correctly, you must not violate any rule.
FOLLOWING THE RULES IS MANDATORY.
1. Write ONLY the pseudocode, NO explanations, NO markdown, NO extra text.
2. Perfect 4-space indentation, one blank line between sections.
3. Define necessary classes at the top.
4. Write function signature, adding rows/cols/depth if arrays are mentioned.
5. Declare ALL local variables immediately after begin, including loop indices.
6. Use parameters for dimensions, do NOT declare or assign them locally.
7. Nest else-if inside else's begin-end.
8. Use call/CALL for user-defined function calls.
9. If Graph g is a parameter, use numeric IDs for graph operations.
10. FINAL CHECK: For every `var class ClassName`, ensure `class ClassName { ... }` exists at the top.
11. FINAL CHECK: Replace contains(), indexOf(), push(), pop() with manual loops if found.
Convert the following natural language description into 100%% valid, parseable pseudocode following ALL 27 rules above without a single exception.
Generate ONLY the pseudocode for this input:
%s
"""

SYSTEM_INSTRUCTIONS_SIMPLIFIED = """You are a pseudocode generator. Convert the following natural-language description into simple pseudocode that follows these rules:  
1. Use `functionName(params) begin ... end` for functions.
2. Use `var` for local declarations.
3. Use `<-` for assignments; `=` only for comparisons.
4. Use `CALL helper(...)` for user functions; built-ins (print, concat, substring, strlen, ceil, floor, length, addNode, addEdge, neighbors) are called without CALL.
5. Use `return expression` (never bare `return`).
6. Use `for i <- start to end do begin ... end` for loops.
7. Use `while (condition) do begin ... end` for while loops.
8. Use `repeat ... until (condition)` for repeat loops (no begin/end inside repeat).
9. Use begin/end blocks for nested `if`/`else`; no “else if”.
10. Use `# ...` for comments.
Given the following natural-language description, generate simple pseudocode according to the above rules. Output ONLY the pseudocode, nothing else:
%s
"""

SYSTEM_INSTRUCTIONS_FIXER = """YOU ARE A STRICT SYNTAX CORRECTOR FOR THE CUSTOM PSEUDOCODE LANGUAGE.
Repair the provided pseudocode so it compiles with the documented grammar without changing the algorithmic intent.
Return ONLY the corrected pseudocode (no explanations, no markdown). Respect the following:
- Preserve function/class names and parameters unless they violate the grammar (add missing rows/cols parameters when arrays appear).
- Ensure begin/end pairing, arrow assignments (<-), CALL prefixes on user procedures, and immediate declaration of loop counters.
- If a fragment truly cannot be repaired, leave a single comment line starting with '# unable to fix: <reason>'.

ORIGINAL CODE:
{pseudocode}

PARSER / VALIDATION ERRORS:
{errors}
"""

WEIGHT_CRITICAL = 3.0
WEIGHT_STRONG = 2.0
WEIGHT_MEDIUM = 1.0
WEIGHT_WEAK = 0.5

WEIGHT_HUMAN_LANGUAGE = 2.5
WEIGHT_EXPLANATORY_HIGH = 3.0
WEIGHT_EXPLANATORY_VERY_HIGH = 2.0

EXPLANATORY_RATIO_LOW = 0.2
EXPLANATORY_RATIO_MEDIUM = 0.25
EXPLANATORY_RATIO_HIGH = 0.3
EXPLANATORY_RATIO_VERY_HIGH = 0.4
EXPLANATORY_RATIO_EXTREMELY_HIGH = 0.5
EXPLANATORY_RATIO_DOMINANT = 0.6
EXPLANATORY_RATIO_THRESHOLD = 0.2

CODE_RATIO_THRESHOLD = 0.5

NL_STRONG_SCORE_LOW = 1.5
NL_STRONG_SCORE_MEDIUM = 2.0
NL_STRONG_SCORE_HIGH = 2.5
NL_STRONG_SCORE_VERY_HIGH = 3.0

PSEUDO_STRONG_SCORE_THRESHOLD = 3.0
PSEUDOCODE_TOTAL_THRESHOLD = 3.0
PSEUDOCODE = "pseudocode"

PSEUDOCODE_STRONG_THRESHOLD = 5.0
NATURAL_LANGUAGE_STRONG_THRESHOLD = 3.0
NATURAL_LANGUAGE_MEDIUM_THRESHOLD = 1.5
NATURAL_LANGUAGE = "natural_language"

LLM_TEMPERATURE_DETERMINISTIC = 0.1
LLM_TEMPERATURE_CREATIVE = 0.3
LLM_MAX_TOKENS = 4000
LLM_MAX_INPUT_LENGTH = 4000
LLM_TIMEOUT_SECONDS = 30
LLM_ENABLE_VERIFICATION = False
LLM_ENABLE_EXPLANATION = False

LLM_MODELS = {
    "openai": "gpt-4o-mini",
    "github": "gpt-3.5-turbo",
    "anthropic": "claude-3-5-sonnet-20241022",
    "google": "gemini-2.5-flash",
}

TOKEN_COSTS = {
    "openai": {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    },
    "anthropic": {
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    },
    "google": {
        "gemini-1.5-pro": {"input": 0.00035, "output": 0.00105},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    },
}


GOOGLE_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

GEMINI_FINISH_REASON_SAFETY = 2
GEMINI_FINISH_REASON_RECITATION = 3
GEMINI_FINISH_REASON_OTHER = 4

SHORT_INPUT_LENGTH = 200

DATA_DIR = "data"
LOG_COLLECTION_LLM_CALLS = "llm_calls"
LOG_COLLECTION_SANITIZATION = "sanitization_logs"
LOG_COLLECTION_POLICY_EVENTS = "policy_events"
SANITIZATION_HASH_SALT = "sanitizer_v1"


TRANSLATION_STRATEGIES = ["standard", "simplified"]
MIN_PSEUDOCODE_LENGTH = 10

STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_VALIDATION_FAILED = "validation_failed"

PATTERN_LABELS = [
    "divide_and_conquer",
    "dynamic_programming",
    "greedy",
    "backtracking",
    "brute_force",
    "graph_algorithms",
    "sorting",
]


ALGORITHM_PATTERNS = {
    "divide_and_conquer": {
        "examples": ["merge_sort", "quick_sort", "binary_search", "closest_pair"],
        "time_complexity": ["O(n log(n))", "O(log(n))", "O(n^2)"],
        "characteristics": ["recursive", "split problem", "combine results"],
    },
    "dynamic_programming": {
        "examples": [
            "fibonacci_memo",
            "knapsack",
            "longest_common_subsequence",
            "edit_distance",
        ],
        "time_complexity": ["O(n)", "O(n*m)", "O(n^2)"],
        "characteristics": ["memoization", "tabulation", "overlapping subproblems"],
    },
    "greedy": {
        "examples": [
            "dijkstra",
            "prim",
            "kruskal",
            "activity_selection",
            "huffman",
        ],
        "time_complexity": ["O(n log(n))", "O(n^2)", "O(E log(V))"],
        "characteristics": ["local optimum", "greedy choice", "no backtracking"],
    },
    "backtracking": {
        "examples": ["n_queens", "sudoku_solver", "hamiltonian_path", "subset_sum"],
        "time_complexity": ["O(n!)", "O(2^n)", "O(n^m)"],
        "characteristics": ["explore all paths", "prune invalid", "recursive"],
    },
    "brute_force": {
        "examples": [
            "linear_search",
            "bubble_sort",
            "selection_sort",
            "naive_string_match",
        ],
        "time_complexity": ["O(n)", "O(n^2)", "O(n*m)"],
        "characteristics": [
            "try all possibilities",
            "nested loops",
            "simple logic",
        ],
    },
    "graph_algorithms": {
        "examples": ["dfs", "bfs", "topological_sort", "strongly_connected"],
        "time_complexity": ["O(V+E)", "O(V^2)", "O(E log(V))"],
        "characteristics": ["graph traversal", "adjacency", "vertices and edges"],
    },
    "sorting": {
        "examples": ["merge_sort", "heap_sort", "counting_sort", "radix_sort"],
        "time_complexity": ["O(n log(n))", "O(n+k)", "O(d*(n+k))"],
        "characteristics": ["comparison based", "divide and conquer", "in-place"],
    },
}


COMPLEXITY_RANK_ORDER = {
    "O(1)": 0,
    "O(log(n))": 1,
    "O(n)": 2,
    "O(n log(n))": 3,
    "O(n^2)": 4,
    "O(n^3)": 5,
    "O(2^n)": 6,
    "O(n!)": 7,
}

PATTERNS = {
    "fibonacci_naive": {
        "keywords": ["fibonacci", "fib"],
        "characteristics": ["recursive", "two_calls", "n-1", "n-2"],
        "complexity": {"best": "O(2^n)", "avg": "O(2^n)", "worst": "O(2^n)"},
        "note": "Naive recursive Fibonacci",
    },
    "fibonacci_memoized": {
        "keywords": ["fibonacci", "fib", "memo"],
        "characteristics": ["recursive", "memoization", "cache"],
        "complexity": {"best": "O(n)", "avg": "O(n)", "worst": "O(n)"},
        "note": "Memoized Fibonacci",
    },
    "binary_search": {
        "keywords": ["binary", "search", "bsearch"],
        "characteristics": ["recursive", "n/2", "divide"],
        "complexity": {
            "best": "O(1)",
            "avg": "O(log(n))",
            "worst": "O(log(n))",
        },
        "note": "Binary search",
    },
    "linear_search": {
        "keywords": ["linear", "search", "find", "sequential"],
        "characteristics": ["loop", "n", "single_level"],
        "complexity": {"best": "O(1)", "avg": "O(n)", "worst": "O(n)"},
        "note": "Linear search - best case when element is first",
    },
    "bubble_sort": {
        "keywords": ["bubble", "sort"],
        "characteristics": ["nested_loops", "swap", "compare"],
        "complexity": {"best": "O(n)", "avg": "O(n^2)", "worst": "O(n^2)"},
        "note": "Bubble sort - best case when already sorted",
    },
    "selection_sort": {
        "keywords": ["selection", "sort"],
        "characteristics": ["nested_loops", "minimum", "select"],
        "complexity": {"best": "O(n^2)", "avg": "O(n^2)", "worst": "O(n^2)"},
        "note": "Selection sort - always O(n^2)",
    },
    "insertion_sort": {
        "keywords": ["insertion", "sort", "insert"],
        "characteristics": ["nested_loops", "shift", "insert"],
        "complexity": {"best": "O(n)", "avg": "O(n^2)", "worst": "O(n^2)"},
        "note": "Insertion sort - best case when already sorted",
    },
    "merge_sort": {
        "keywords": ["mergesort"],
        "characteristics": ["recursive", "n/2", "merge", "divide"],
        "complexity": {
            "best": "O(n log(n))",
            "avg": "O(n log(n))",
            "worst": "O(n log(n))",
        },
        "note": "Merge sort - always O(n log(n))",
    },
    "merge_arrays": {
        "keywords": ["merge", "sorted", "arrays"],
        "characteristics": ["loop", "compare", "two_arrays"],
        "complexity": {
            "best": "O(n)",
            "avg": "O(n)",
            "worst": "O(n)",
        },
        "note": "Merging two sorted arrays - linear time O(n+m)",
    },
    "quick_sort": {
        "keywords": ["quick", "sort", "partition"],
        "characteristics": ["recursive", "partition", "pivot"],
        "complexity": {
            "best": "O(n log(n))",
            "avg": "O(n log(n))",
            "worst": "O(n^2)",
        },
        "note": "Quick sort - worst case when poorly partitioned",
    },
    "dfs": {
        "keywords": ["dfs", "depth", "first"],
        "characteristics": ["recursive", "visited", "neighbors"],
        "complexity": {"best": "O(V+E)", "avg": "O(V+E)", "worst": "O(V+E)"},
        "note": "Depth-first search",
    },
    "bfs": {
        "keywords": ["bfs", "breadth", "first", "queue"],
        "characteristics": ["loop", "queue", "visited", "neighbors"],
        "complexity": {"best": "O(V+E)", "avg": "O(V+E)", "worst": "O(V+E)"},
        "note": "Breadth-first search",
    },
    "knapsack_dp": {
        "keywords": ["knapsack", "dp", "weight", "value"],
        "characteristics": ["nested_loops", "table", "dp"],
        "complexity": {"best": "O(n*W)", "avg": "O(n*W)", "worst": "O(n*W)"},
        "note": "0/1 Knapsack with DP",
    },
    "lcs": {
        "keywords": ["lcs", "longest", "common", "subsequence"],
        "characteristics": ["nested_loops", "table", "dp"],
        "complexity": {"best": "O(m*n)", "avg": "O(m*n)", "worst": "O(m*n)"},
        "note": "Longest Common Subsequence",
    },
    "two_pointers": {
        "keywords": ["two", "pointer", "left", "right"],
        "characteristics": ["loop", "pointers", "linear"],
        "complexity": {"best": "O(n)", "avg": "O(n)", "worst": "O(n)"},
        "note": "Two pointers technique",
    },
    "sliding_window": {
        "keywords": ["sliding", "window", "subarray"],
        "characteristics": ["loop", "window", "deque"],
        "complexity": {"best": "O(n)", "avg": "O(n)", "worst": "O(n)"},
        "note": "Sliding window technique",
    },
}
