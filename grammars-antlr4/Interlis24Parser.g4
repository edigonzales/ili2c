parser grammar Interlis24Parser;

options { tokenVocab=Interlis24Lexer; }

iliFile: INTERLIS version SEMICOLON model+ EOF;

version: NUMBER DOT NUMBER;

model: MODEL ID languageSpec? modelHeader? EQUALS modelBody END ID DOT;

languageSpec: LPAREN ID RPAREN;

modelHeader: (AT STRING)? (VERSION STRING)?;

modelBody: statement*;

statement
    : topic
    | classDef
    | structureDef
    | associationDef
    | domainSection
    | functionDef
    | constraintDef
    | importsStmt
    | SEMICOLON
    ;

topic: TOPIC ID modelHeader? EQUALS topicBody END ID SEMICOLON;

topicBody: topicStatement*;

topicStatement
    : classDef
    | structureDef
    | associationDef
    | domainSection
    | functionDef
    | constraintDef
    | dependsStmt
    | SEMICOLON
    ;

importsStmt: IMPORTS qualifiedName (COMMA qualifiedName)* SEMICOLON;

domainSection: DOMAIN domainStatement+;

domainStatement: ID EQUALS domainType SEMICOLON;

domainType: enumerationType | typeRef;

enumerationType: LPAREN enumItem (COMMA enumItem)* RPAREN;

enumItem: ID | STRING;

classDef: CLASS ID classModifiers? (EXTENDS qualifiedName)? EQUALS classElement* END ID SEMICOLON;

structureDef: STRUCTURE ID classModifiers? (EXTENDS qualifiedName)? EQUALS classElement* END ID SEMICOLON;

classModifiers: LPAREN ABSTRACT RPAREN;

classElement
    : attrDef
    | constraintDef
    | uniqueDef
    | SEMICOLON
    ;

uniqueDef: UNIQUE uniqueExprList SEMICOLON;

uniqueExprList: uniqueExpr (COMMA uniqueExpr)*;

uniqueExpr: qualifiedName;

associationDef: ASSOCIATION ID EQUALS associationElement* END ID SEMICOLON;

associationElement
    : roleDef
    | constraintDef
    | SEMICOLON
    ;

roleDef: ID roleModifier? ASSOC_ARROW roleCardinality? qualifiedName SEMICOLON;

roleModifier: LPAREN EXTERNAL RPAREN;

roleCardinality: LBRACE NUMBER (RANGE (NUMBER | STAR))? RBRACE;

dependsStmt: DEPENDS ON qualifiedName SEMICOLON;

functionDef: FUNCTION ID LPAREN paramList? RPAREN (COLON typeRef)? SEMICOLON;

paramList: param (COMMA param)*;

param: ID COLON typeRef;

attrDef: ID cardinality? COLON mandatoryAttr? (enumerationType | typeRef) SEMICOLON;

mandatoryAttr: MANDATORY;

cardinality: LSQUARE NUMBER (RANGE (NUMBER | STAR))? RSQUARE;

typeRef
    : BAG listCardinality? OF typeRef
    | LIST listCardinality? OF typeRef
    | qualifiedName typeSuffix*
    | numericRange
    ;

typeSuffix
    : STAR NUMBER
    | RANGE (NUMBER | STAR)
    ;

numericRange: NUMBER RANGE NUMBER;

listCardinality: LBRACE NUMBER RANGE (NUMBER | STAR) RBRACE;

qualifiedName: identifier (DOT identifier)*;

identifier: ID | INTERLIS;

constraintDef: (MANDATORY)? CONSTRAINT constraintExpression SEMICOLON;

constraintExpression: exprToken+;

exprToken
    : ID
    | NUMBER
    | STRING
    | LPAREN
    | RPAREN
    | COMMA
    | DOT
    | GT
    | STAR
    | RANGE
    | LBRACE
    | RBRACE
    | EQUALS
    ;
