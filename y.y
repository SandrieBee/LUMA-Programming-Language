%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern char* get_current_line();
extern void reset_line_buffer();

extern int yylex();
extern void yyerror(const char *s);
extern int yylineno;

int lineCount = 1, cntr = 0;
int error_occurred = 0;

typedef struct {
   int errValue;
} errorList;
errorList list[40];

// Symbol table structure
typedef struct {
    char *name;
    int type;
    // 0=int, 1=float, 2=char, 3=string, -1=uninitialized
    union {
        int ival;
        double fval;
        char cval;
        char *sval;
    } value;
    int initialized;
} symbol;

symbol symbol_table[100];
int symbol_count = 0;

int lookup_symbol(char *name);
void add_symbol(char *name);
void update_symbol_val(char *name, int type, double fval, char *sval, char cval);
void get_variable_value(char *name, double *fval, char **sval, char *cval, int *type, int *error);

// Helper function to execute line logic
void execute_line(); 
int checkError(int errVal, int currentLine);
%}

%union {
    int ival;
    double fval;
    char cval;
    char *sval;
    // Unified expression value
    struct {
        double fval;
        char *sval;
        char cval;
        int type; // 0=int, 1=float, 2=char, 3=string
    } expr_val;
}

%token NEWLINE
%token LET DISPLAY ASSIGN COMMA
%token LPAREN RPAREN
%token <ival> INT_VAL
%token <fval> FLOAT_VAL
%token <cval> CHAR_VAL
%token <sval> STRING_VAL
%token <sval> IDENTIFIER
%token PLUS MINUS MULT DIV

%left PLUS MINUS
%left MULT DIV

%type <expr_val> expression term factor

%%

/* UPDATED GRAMMAR STRUCTURE */
program:        line_list
                | statement { execute_line(); }
                | line_list statement { execute_line(); }
                ;

line_list:      line_list line
                | line
                ;

line:           statement NEWLINE { 
                    execute_line(); 
                    ++lineCount; 
                }
                | error NEWLINE { yyerrok; ++lineCount; }
                | NEWLINE { ++lineCount; }
                ;

statement:      var_decl
                | assignment_stmt
                | print_stmt
                ;

var_decl:       LET assignment_list
                ;

assignment_list: decl_item
                | assignment_list COMMA decl_item
                ;

decl_item:      IDENTIFIER ASSIGN expression
                {
                    add_symbol($1);
                    update_symbol_val($1, $3.type, $3.fval, $3.sval, $3.cval);
                    free($1);
                    if ($3.type == 3 && $3.sval) free($3.sval);
                }
                | IDENTIFIER
                {
                    add_symbol($1);
                    free($1);
                }
                ;

assignment_stmt: assignment
                | assignment_stmt COMMA assignment
                ;

assignment:     IDENTIFIER ASSIGN expression
                {
                    int idx = lookup_symbol($1);
                    if (idx >= 0) {
                        update_symbol_val($1, $3.type, $3.fval, $3.sval, $3.cval);
                    } else {
                        char buf[256];
                        sprintf(buf, "Variable '%s' not declared", $1);
                        yyerror(buf);
                    }
                    free($1);
                    if ($3.type == 3 && $3.sval) free($3.sval);
                }
                ;

print_stmt:     DISPLAY expression
                {
                    switch($2.type) {
                        case 0: printf("%d\n", (int)$2.fval); break;
                        case 1: printf("%.2f\n", $2.fval); break;
                        case 2: printf("%c\n", $2.cval); break;
                        case 3: printf("%s\n", $2.sval); free($2.sval); break;
                    }
                }
                ;

expression:     expression PLUS term 
                { 
                    if ($1.type == 3 || $3.type == 3) {
                        /* String Concatenation */
                        $$.type = 3; $$.fval = 0; $$.cval = 0;
                        char buf1[100], buf2[100];
                        char *s1 = buf1, *s2 = buf2;
                        
                        if ($1.type == 0) sprintf(buf1, "%d", (int)$1.fval);
                        else if ($1.type == 1) sprintf(buf1, "%.2f", $1.fval);
                        else if ($1.type == 2) sprintf(buf1, "%c", $1.cval);
                        else s1 = $1.sval;

                        if ($3.type == 0) sprintf(buf2, "%d", (int)$3.fval);
                        else if ($3.type == 1) sprintf(buf2, "%.2f", $3.fval);
                        else if ($3.type == 2) sprintf(buf2, "%c", $3.cval);
                        else s2 = $3.sval;

                        $$.sval = malloc(strlen(s1) + strlen(s2) + 1);
                        strcpy($$.sval, s1);
                        strcat($$.sval, s2);
                        
                        if ($1.type == 3) free($1.sval);
                        if ($3.type == 3) free($3.sval);
                    } else {
                        $$.fval = $1.fval + $3.fval;
                        $$.type = ($1.type == 1 || $3.type == 1) ? 1 : 0;
                        $$.sval = NULL;
                    }
                }
                | expression MINUS term 
                { 
                    if ($1.type == 3 || $3.type == 3) {
                        yyerror("Cannot subtract strings");
                        $$.fval = 0; $$.type = 0;
                    } else {
                        $$.fval = $1.fval - $3.fval;
                        $$.type = ($1.type == 1 || $3.type == 1) ? 1 : 0;
                    }
                    $$.sval = NULL;
                }
                | term { $$ = $1; }
                ;

term:           term MULT factor 
                { 
                    if ($1.type == 3 || $3.type == 3) {
                         yyerror("Cannot multiply strings");
                         $$.fval = 0; $$.type = 0;
                    } else {
                        $$.fval = $1.fval * $3.fval;
                        $$.type = ($1.type == 1 || $3.type == 1) ? 1 : 0;
                    }
                    $$.sval = NULL;
                }
                | term DIV factor 
                { 
                    if ($1.type == 3 || $3.type == 3) {
                         yyerror("Cannot divide strings");
                         $$.fval = 0; $$.type = 0;
                    } else {
                        if ($3.fval == 0) {
                            yyerror("Division by zero");
                            $$.fval = 0; $$.type = 1;
                        } else {
                            $$.fval = $1.fval / $3.fval;
                            $$.type = ($1.type == 1 || $3.type == 1) ? 1 : 0;
                        }
                    }
                    $$.sval = NULL;
                }
                | factor { $$ = $1; }
                ;

factor:         LPAREN expression RPAREN { $$ = $2; }
                | INT_VAL { $$.fval = (double)$1; $$.type = 0; $$.sval = NULL; }
                | FLOAT_VAL { $$.fval = $1; $$.type = 1; $$.sval = NULL; }
                | CHAR_VAL { $$.cval = $1; $$.fval = (double)$1; $$.type = 2; $$.sval = NULL; }
                | STRING_VAL { $$.sval = strdup($1); $$.type = 3; free($1); }
                | IDENTIFIER {
                    int error = 0;
                    int type = 0;
                    get_variable_value($1, &$$.fval, &$$.sval, &$$.cval, &type, &error);
                    if (error) {
                        char buf[256];
                        sprintf(buf, "Variable '%s' not initialized", $1);
                        yyerror(buf);
                        $$.fval = 0; $$.type = 0; $$.sval = NULL;
                    } else {
                        $$.type = type;
                    }
                    free($1);
                }
                ;
%%

/* Helper function to process errors for the current line */
void execute_line() {
    int x, result = 0;
    for(x = 1; x <= cntr; x++){
        result = checkError(list[x].errValue, lineCount);
        if(result > 0){ break; }
    }
    // Note: lineCount is not incremented here; rules handle that
}

int checkError(int errVal, int currentLine) {
    if (errVal == currentLine) return 1;
    return 0;
}

int lookup_symbol(char *name) {
    for (int i = 0; i < symbol_count; i++) {
        if (strcmp(symbol_table[i].name, name) == 0) return i;
    }
    return -1;
}

void add_symbol(char *name) {
    int idx = lookup_symbol(name);
    if (idx >= 0) return;
    if (symbol_count >= 100) {
        fprintf(stderr, "Symbol table full\n");
        return;
    }
    symbol_table[symbol_count].name = strdup(name);
    symbol_table[symbol_count].type = -1;
    symbol_table[symbol_count].initialized = 0;
    symbol_count++;
}

void update_symbol_val(char *name, int type, double fval, char *sval, char cval) {
    int idx = lookup_symbol(name);
    if (idx >= 0) {
        if (symbol_table[idx].type == 3 && symbol_table[idx].value.sval != NULL) {
            free(symbol_table[idx].value.sval);
        }
        symbol_table[idx].type = type;
        symbol_table[idx].initialized = 1;
        switch(type) {
            case 0: symbol_table[idx].value.ival = (int)fval; break;
            case 1: symbol_table[idx].value.fval = fval; break;
            case 2: symbol_table[idx].value.cval = cval; break;
            case 3: symbol_table[idx].value.sval = strdup(sval); break;
        }
    }
}

void get_variable_value(char *name, double *fval, char **sval, char *cval, int *type, int *error) {
    int idx = lookup_symbol(name);
    *error = 0;
    if (idx < 0 || !symbol_table[idx].initialized) {
        *error = 1;
        return;
    }
    *type = symbol_table[idx].type;
    switch (*type) {
        case 0: *fval = (double)symbol_table[idx].value.ival; break;
        case 1: *fval = symbol_table[idx].value.fval; break;
        case 2: *cval = symbol_table[idx].value.cval; *fval = (double)*cval; break;
        case 3: *sval = strdup(symbol_table[idx].value.sval); break;
    }
}

int main(void) {
    yyparse();
    return error_occurred;
}

void yyerror(const char *s) {
    error_occurred = 1;
    fflush(stdout);
    list[++cntr].errValue = lineCount;
    char *problem_line = get_current_line();
    
    fprintf(stderr, "\n");
    fprintf(stderr, "!! Error (%s)\n", s);
    fprintf(stderr, "~ ~ LINE %d: %s ~ ~\n", lineCount, problem_line);
    fprintf(stderr, "\n");
}