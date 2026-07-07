%{
// Scanner for Luma Language
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "y.tab.h"

void yyerror(const char *s);
// Line buffer for error reporting
char current_line[1024] = "";
int current_line_pos = 0;

void save_to_line_buffer(char *text) {
    int len = strlen(text);
    if (current_line_pos + len < 1023) {
        strcpy(current_line + current_line_pos, text);
        current_line_pos += len;
    }
}

void reset_line_buffer() {
    current_line[0] = '\0';
    current_line_pos = 0;
}

char* get_current_line() {
    return current_line;
}

// Function to process escape sequences in strings
char* process_escape_sequences(char *str) {
    char *result = malloc(strlen(str) + 1);
    int i, j = 0;
    
    for (i = 0; str[i] != '\0'; i++) {
        if (str[i] == '\\' && str[i+1] != '\0') {
            switch (str[i+1]) {
                case 'n':  result[j++] = '\n'; i++; break;
                case 't':  result[j++] = '\t'; i++; break;
                case 'r':  result[j++] = '\r'; i++; break;
                case '\\': result[j++] = '\\'; i++; break;
                case '"':  result[j++] = '"';  i++; break;
                default:   result[j++] = str[i]; break;
            }
        } else {
            result[j++] = str[i];
        }
    }
    result[j] = '\0';
    return result;
}

%}

%option yylineno
%x MULTILINE_COMMENT

%%

"$"                    { save_to_line_buffer(yytext); BEGIN(MULTILINE_COMMENT); }
<MULTILINE_COMMENT>"$" { save_to_line_buffer(yytext); BEGIN(INITIAL); }
<MULTILINE_COMMENT>\n  { save_to_line_buffer(yytext); }
<MULTILINE_COMMENT>.   { save_to_line_buffer(yytext); }

"$"[^\n]* { save_to_line_buffer(yytext); /* Single line comment */ }

[ \t\r]+               { save_to_line_buffer(yytext); } 

\r\n|\n                { 
                          reset_line_buffer(); 
                          return NEWLINE;
                       }

"let"                  { save_to_line_buffer(yytext); return LET; }
"display"              { save_to_line_buffer(yytext); return DISPLAY; }

[0-9]+\.[0-9]+         { 
                          save_to_line_buffer(yytext);
                          yylval.fval = atof(yytext); 
                          return FLOAT_VAL; 
                       }
                        
[0-9]+                 { 
                          save_to_line_buffer(yytext);
                          yylval.ival = atoi(yytext); 
                          return INT_VAL; 
                       }

'[a-zA-Z0-9_]'         { 
                          save_to_line_buffer(yytext);
                          yylval.cval = yytext[1]; 
                          return CHAR_VAL; 
                       }

\'[^'\n]{2,}\'         { 
                          save_to_line_buffer(yytext);
                          yyerror("Error: Single quotes can only hold ONE character. Use double quotes \"...\" for strings.");
                       }

\"(\\.|[^"\\])*\"      { 
                          /* Updated Regex: correctly handles escaped quotes inside strings */
                          save_to_line_buffer(yytext);
                          char *raw_string = strdup(yytext + 1);
                          raw_string[strlen(raw_string) - 1] = '\0';
                          yylval.sval = process_escape_sequences(raw_string);
                          free(raw_string);
                          return STRING_VAL; 
                       }

[a-zA-Z_][a-zA-Z0-9_]* { 
                          save_to_line_buffer(yytext);
                          yylval.sval = strdup(yytext); 
                          return IDENTIFIER; 
                       }

","                    { save_to_line_buffer(yytext); return COMMA; }
"="                    { save_to_line_buffer(yytext); return ASSIGN; }
"+"                    { save_to_line_buffer(yytext); return PLUS; }
"-"                    { save_to_line_buffer(yytext); return MINUS; }
"*"                    { save_to_line_buffer(yytext); return MULT; }
"/"                    { save_to_line_buffer(yytext); return DIV; }
"("                    { save_to_line_buffer(yytext); return LPAREN; }
")"                    { save_to_line_buffer(yytext); return RPAREN; }

.                      { 
                          save_to_line_buffer(yytext);
                          yyerror("Invalid Character"); 
                       }

%%

int yywrap(void){ return 1; }