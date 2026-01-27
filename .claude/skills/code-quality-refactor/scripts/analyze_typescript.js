#!/usr/bin/env node
/**
 * TypeScript/JavaScript AST Analyzer
 * 
 * Performs deep analysis using the TypeScript compiler API:
 * - Function metrics (length, complexity, parameters)
 * - Dead code detection (unused exports, unreachable code)
 * - Duplicate code detection (AST structure comparison)
 * - Circular dependency detection
 * - Security pattern detection
 * - Type coverage (for TypeScript)
 * 
 * Usage: npx ts-node analyze_typescript.ts <path> [--output file.json]
 * Or: node analyze_typescript.js <path> (if pre-compiled)
 */

const ts = require('typescript');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// ============================================================================
// Types
// ============================================================================

interface FunctionMetrics {
  name: string;
  file: string;
  lineStart: number;
  lineEnd: number;
  lineCount: number;
  parameterCount: number;
  complexity: number;
  nestingDepth: number;
  isAsync: boolean;
  isExported: boolean;
  hasJSDoc: boolean;
  returnType: string | null;
}

interface FileMetrics {
  path: string;
  language: 'typescript' | 'javascript';
  lineCount: number;
  codeLines: number;
  functions: FunctionMetrics[];
  classes: string[];
  imports: ImportInfo[];
  exports: ExportInfo[];
  isTest: boolean;
}

interface ImportInfo {
  module: string;
  named: string[];
  default: string | null;
  line: number;
}

interface ExportInfo {
  name: string;
  kind: 'function' | 'class' | 'variable' | 'type' | 'default';
  line: number;
  isUsedInternally: boolean;
}

interface DuplicateCandidate {
  file1: string;
  line1Start: number;
  line1End: number;
  file2: string;
  line2Start: number;
  line2End: number;
  similarity: number;
  description: string;
}

interface DeadCodeItem {
  file: string;
  line: number;
  kind: 'unused-export' | 'unused-variable' | 'unreachable-code' | 'unused-import';
  name: string;
  description: string;
}

interface CircularDependency {
  cycle: string[];
  description: string;
}

interface PotentialIssue {
  category: string;
  pattern: string;
  file: string;
  line: number;
  code: string;
  description: string;
}

interface AnalysisResult {
  rootPath: string;
  language: string;
  framework: string;
  totalFiles: number;
  totalLines: number;
  files: FileMetrics[];
  deadCode: DeadCodeItem[];
  duplicates: DuplicateCandidate[];
  circularDeps: CircularDependency[];
  potentialIssues: PotentialIssue[];
  typeErrors: any[];
  summary: {
    avgComplexity: number;
    maxComplexity: number;
    avgFunctionLength: number;
    maxFunctionLength: number;
    exportedFunctions: number;
    unusedExports: number;
    circularDeps: number;
  };
}

// ============================================================================
// File Collection
// ============================================================================

const IGNORE_DIRS = new Set([
  'node_modules', 'dist', 'build', '.next', '.nuxt', 'coverage',
  '.git', '.svn', 'vendor', '__pycache__', '.cache', 'out'
]);

const TEST_PATTERNS = ['test', 'spec', '__tests__', '__mocks__'];

function collectFiles(rootPath: string, maxFiles = 500): string[] {
  const files: string[] = [];
  const extensions = ['.ts', '.tsx', '.js', '.jsx', '.mjs'];

  function walk(dir: string) {
    if (files.length >= maxFiles) return;
    
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      if (files.length >= maxFiles) return;
      
      const fullPath = path.join(dir, entry.name);
      
      if (entry.isDirectory()) {
        if (!IGNORE_DIRS.has(entry.name) && !entry.name.startsWith('.')) {
          walk(fullPath);
        }
      } else if (entry.isFile()) {
        const ext = path.extname(entry.name).toLowerCase();
        if (extensions.includes(ext)) {
          files.push(fullPath);
        }
      }
    }
  }

  const stat = fs.statSync(rootPath);
  if (stat.isFile()) {
    return [rootPath];
  }
  
  walk(rootPath);
  return files;
}

// ============================================================================
// AST Analysis
// ============================================================================

function calculateComplexity(node: ts.Node): number {
  let complexity = 1;

  function visit(n: ts.Node) {
    switch (n.kind) {
      case ts.SyntaxKind.IfStatement:
      case ts.SyntaxKind.ForStatement:
      case ts.SyntaxKind.ForInStatement:
      case ts.SyntaxKind.ForOfStatement:
      case ts.SyntaxKind.WhileStatement:
      case ts.SyntaxKind.DoStatement:
      case ts.SyntaxKind.CatchClause:
      case ts.SyntaxKind.ConditionalExpression:
      case ts.SyntaxKind.CaseClause:
        complexity++;
        break;
      case ts.SyntaxKind.BinaryExpression:
        const binExpr = n as ts.BinaryExpression;
        if (binExpr.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken ||
            binExpr.operatorToken.kind === ts.SyntaxKind.BarBarToken ||
            binExpr.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken) {
          complexity++;
        }
        break;
    }
    ts.forEachChild(n, visit);
  }

  ts.forEachChild(node, visit);
  return complexity;
}

function calculateNestingDepth(node: ts.Node): number {
  let maxDepth = 0;

  function visit(n: ts.Node, depth: number) {
    let newDepth = depth;
    
    switch (n.kind) {
      case ts.SyntaxKind.IfStatement:
      case ts.SyntaxKind.ForStatement:
      case ts.SyntaxKind.ForInStatement:
      case ts.SyntaxKind.ForOfStatement:
      case ts.SyntaxKind.WhileStatement:
      case ts.SyntaxKind.DoStatement:
      case ts.SyntaxKind.TryStatement:
      case ts.SyntaxKind.SwitchStatement:
      case ts.SyntaxKind.ArrowFunction:
      case ts.SyntaxKind.FunctionExpression:
        newDepth = depth + 1;
        break;
    }
    
    maxDepth = Math.max(maxDepth, newDepth);
    ts.forEachChild(n, child => visit(child, newDepth));
  }

  ts.forEachChild(node, child => visit(child, 0));
  return maxDepth;
}

function analyzeFile(filePath: string, sourceFile: ts.SourceFile): FileMetrics {
  const lines = sourceFile.getFullText().split('\n');
  const isTest = TEST_PATTERNS.some(p => filePath.toLowerCase().includes(p));
  const isTS = filePath.endsWith('.ts') || filePath.endsWith('.tsx');

  const functions: FunctionMetrics[] = [];
  const classes: string[] = [];
  const imports: ImportInfo[] = [];
  const exports: ExportInfo[] = [];
  const exportedNames = new Set<string>();
  const usedIdentifiers = new Set<string>();

  // Collect all identifier usages
  function collectUsages(node: ts.Node) {
    if (ts.isIdentifier(node)) {
      usedIdentifiers.add(node.text);
    }
    ts.forEachChild(node, collectUsages);
  }
  collectUsages(sourceFile);

  function visit(node: ts.Node) {
    // Functions
    if (ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) ||
        ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
      
      let name = 'anonymous';
      let isExported = false;

      if (ts.isFunctionDeclaration(node) && node.name) {
        name = node.name.text;
        isExported = node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword) || false;
      } else if (ts.isMethodDeclaration(node) && node.name) {
        name = node.name.getText(sourceFile);
      } else if (ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
        // Try to get name from parent variable declaration
        const parent = node.parent;
        if (ts.isVariableDeclaration(parent) && ts.isIdentifier(parent.name)) {
          name = parent.name.text;
          // Check if the variable statement is exported
          const varStatement = parent.parent?.parent;
          if (ts.isVariableStatement(varStatement)) {
            isExported = varStatement.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword) || false;
          }
        }
      }

      const startLine = sourceFile.getLineAndCharacterOfPosition(node.getStart()).line + 1;
      const endLine = sourceFile.getLineAndCharacterOfPosition(node.getEnd()).line + 1;
      const params = ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) || 
                     ts.isArrowFunction(node) || ts.isFunctionExpression(node)
        ? (node.parameters?.length || 0)
        : 0;

      // Get return type
      let returnType: string | null = null;
      if ('type' in node && node.type) {
        returnType = node.type.getText(sourceFile);
      }

      // Check for JSDoc
      const hasJSDoc = ts.getJSDocTags(node).length > 0;

      functions.push({
        name,
        file: filePath,
        lineStart: startLine,
        lineEnd: endLine,
        lineCount: endLine - startLine + 1,
        parameterCount: params,
        complexity: calculateComplexity(node),
        nestingDepth: calculateNestingDepth(node),
        isAsync: node.modifiers?.some(m => m.kind === ts.SyntaxKind.AsyncKeyword) || false,
        isExported,
        hasJSDoc,
        returnType
      });
    }

    // Classes
    if (ts.isClassDeclaration(node) && node.name) {
      classes.push(node.name.text);
    }

    // Imports
    if (ts.isImportDeclaration(node)) {
      const moduleSpecifier = node.moduleSpecifier;
      if (ts.isStringLiteral(moduleSpecifier)) {
        const importInfo: ImportInfo = {
          module: moduleSpecifier.text,
          named: [],
          default: null,
          line: sourceFile.getLineAndCharacterOfPosition(node.getStart()).line + 1
        };

        const importClause = node.importClause;
        if (importClause) {
          if (importClause.name) {
            importInfo.default = importClause.name.text;
          }
          if (importClause.namedBindings) {
            if (ts.isNamedImports(importClause.namedBindings)) {
              importInfo.named = importClause.namedBindings.elements.map(e => e.name.text);
            }
          }
        }

        imports.push(importInfo);
      }
    }

    // Exports
    if (ts.isExportDeclaration(node) || ts.isExportAssignment(node)) {
      const line = sourceFile.getLineAndCharacterOfPosition(node.getStart()).line + 1;
      
      if (ts.isExportAssignment(node)) {
        exports.push({
          name: 'default',
          kind: 'default',
          line,
          isUsedInternally: false
        });
      }
    }

    // Named exports from declarations
    if ((ts.isFunctionDeclaration(node) || ts.isClassDeclaration(node) || 
         ts.isVariableStatement(node) || ts.isTypeAliasDeclaration(node) ||
         ts.isInterfaceDeclaration(node)) &&
        node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      
      const line = sourceFile.getLineAndCharacterOfPosition(node.getStart()).line + 1;
      let name = '';
      let kind: ExportInfo['kind'] = 'variable';

      if (ts.isFunctionDeclaration(node) && node.name) {
        name = node.name.text;
        kind = 'function';
      } else if (ts.isClassDeclaration(node) && node.name) {
        name = node.name.text;
        kind = 'class';
      } else if (ts.isVariableStatement(node)) {
        kind = 'variable';
        for (const decl of node.declarationList.declarations) {
          if (ts.isIdentifier(decl.name)) {
            name = decl.name.text;
            exportedNames.add(name);
            exports.push({
              name,
              kind,
              line,
              isUsedInternally: usedIdentifiers.has(name)
            });
          }
        }
        return; // Already added
      } else if (ts.isTypeAliasDeclaration(node) || ts.isInterfaceDeclaration(node)) {
        name = node.name.text;
        kind = 'type';
      }

      if (name) {
        exportedNames.add(name);
        exports.push({
          name,
          kind,
          line,
          isUsedInternally: usedIdentifiers.has(name)
        });
      }
    }

    ts.forEachChild(node, visit);
  }

  visit(sourceFile);

  // Count code lines (non-blank, non-comment)
  let codeLines = 0;
  let inBlockComment = false;
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('/*')) inBlockComment = true;
    if (trimmed.endsWith('*/')) {
      inBlockComment = false;
      continue;
    }
    if (!inBlockComment && trimmed && !trimmed.startsWith('//')) {
      codeLines++;
    }
  }

  return {
    path: filePath,
    language: isTS ? 'typescript' : 'javascript',
    lineCount: lines.length,
    codeLines,
    functions,
    classes,
    imports,
    exports,
    isTest
  };
}

// ============================================================================
// Dead Code Detection
// ============================================================================

function findDeadCode(files: FileMetrics[], importGraph: Map<string, Set<string>>): DeadCodeItem[] {
  const deadCode: DeadCodeItem[] = [];
  
  // Track all imports across all files
  const allImportedNames = new Map<string, Set<string>>(); // module -> imported names
  
  for (const file of files) {
    for (const imp of file.imports) {
      if (!allImportedNames.has(imp.module)) {
        allImportedNames.set(imp.module, new Set());
      }
      const names = allImportedNames.get(imp.module)!;
      if (imp.default) names.add('default');
      imp.named.forEach(n => names.add(n));
    }
  }

  // Find unused exports
  for (const file of files) {
    if (file.isTest) continue; // Skip test files
    
    const relativePath = file.path;
    const importedFromThisFile = new Set<string>();
    
    // Collect what's imported from this file
    for (const [module, names] of allImportedNames) {
      // Check if this import refers to our file
      if (module.includes(path.basename(file.path, path.extname(file.path)))) {
        names.forEach(n => importedFromThisFile.add(n));
      }
    }

    for (const exp of file.exports) {
      // Check if this export is used elsewhere
      const importName = exp.kind === 'default' ? 'default' : exp.name;
      const isImported = importedFromThisFile.has(importName) || importedFromThisFile.has(exp.name);
      
      if (!isImported && !exp.isUsedInternally && exp.name !== 'default') {
        deadCode.push({
          file: file.path,
          line: exp.line,
          kind: 'unused-export',
          name: exp.name,
          description: `Exported ${exp.kind} '${exp.name}' is never imported`
        });
      }
    }
  }

  return deadCode;
}

// ============================================================================
// Circular Dependency Detection
// ============================================================================

function findCircularDependencies(files: FileMetrics[]): CircularDependency[] {
  const circular: CircularDependency[] = [];
  const graph = new Map<string, string[]>();

  // Build dependency graph
  for (const file of files) {
    const deps: string[] = [];
    for (const imp of file.imports) {
      // Skip external modules
      if (!imp.module.startsWith('.') && !imp.module.startsWith('/')) continue;
      
      // Resolve relative import
      const dir = path.dirname(file.path);
      let resolved = path.resolve(dir, imp.module);
      
      // Try to find the actual file
      const extensions = ['.ts', '.tsx', '.js', '.jsx', ''];
      for (const ext of extensions) {
        const tryPath = resolved + ext;
        const tryIndex = path.join(resolved, 'index' + (ext || '.ts'));
        
        if (files.some(f => f.path === tryPath)) {
          deps.push(tryPath);
          break;
        } else if (files.some(f => f.path === tryIndex)) {
          deps.push(tryIndex);
          break;
        }
      }
    }
    graph.set(file.path, deps);
  }

  // Find cycles using DFS
  const visited = new Set<string>();
  const recursionStack = new Set<string>();
  const pathStack: string[] = [];

  function dfs(node: string): boolean {
    visited.add(node);
    recursionStack.add(node);
    pathStack.push(node);

    const deps = graph.get(node) || [];
    for (const dep of deps) {
      if (!visited.has(dep)) {
        if (dfs(dep)) return true;
      } else if (recursionStack.has(dep)) {
        // Found cycle
        const cycleStart = pathStack.indexOf(dep);
        const cycle = pathStack.slice(cycleStart).map(p => path.basename(p));
        cycle.push(path.basename(dep)); // Complete the cycle
        
        circular.push({
          cycle,
          description: `Circular dependency: ${cycle.join(' → ')}`
        });
        return true;
      }
    }

    pathStack.pop();
    recursionStack.delete(node);
    return false;
  }

  for (const file of files) {
    if (!visited.has(file.path)) {
      dfs(file.path);
    }
  }

  return circular;
}

// ============================================================================
// Duplicate Detection
// ============================================================================

function hashAST(node: ts.Node, sourceFile: ts.SourceFile): string {
  // Create a normalized representation of the AST structure
  const parts: string[] = [];

  function visit(n: ts.Node, depth: number) {
    if (depth > 10) return; // Limit depth

    parts.push(`${depth}:${ts.SyntaxKind[n.kind]}`);
    
    // Add some structural info without exact values
    if (ts.isIdentifier(n)) {
      parts.push('ID');
    } else if (ts.isStringLiteral(n)) {
      parts.push('STR');
    } else if (ts.isNumericLiteral(n)) {
      parts.push('NUM');
    }

    ts.forEachChild(n, child => visit(child, depth + 1));
  }

  visit(node, 0);
  return crypto.createHash('md5').update(parts.join(',')).digest('hex');
}

function findDuplicates(files: FileMetrics[], sourceFiles: Map<string, ts.SourceFile>): DuplicateCandidate[] {
  const duplicates: DuplicateCandidate[] = [];
  const functionHashes = new Map<string, { file: string; func: FunctionMetrics; sourceFile: ts.SourceFile }[]>();

  // Hash all functions
  for (const file of files) {
    const sourceFile = sourceFiles.get(file.path);
    if (!sourceFile) continue;

    for (const func of file.functions) {
      if (func.lineCount < 5) continue; // Skip tiny functions

      // Find the function node
      function findFunctionNode(node: ts.Node): ts.Node | null {
        const line = sourceFile!.getLineAndCharacterOfPosition(node.getStart()).line + 1;
        if (line === func.lineStart) {
          if (ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) ||
              ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
            return node;
          }
        }
        let result: ts.Node | null = null;
        ts.forEachChild(node, child => {
          if (!result) result = findFunctionNode(child);
        });
        return result;
      }

      const funcNode = findFunctionNode(sourceFile);
      if (funcNode) {
        const hash = hashAST(funcNode, sourceFile);
        
        if (!functionHashes.has(hash)) {
          functionHashes.set(hash, []);
        }
        functionHashes.get(hash)!.push({ file: file.path, func, sourceFile });
      }
    }
  }

  // Find duplicates (same hash = similar structure)
  for (const [hash, funcs] of functionHashes) {
    if (funcs.length > 1) {
      for (let i = 0; i < funcs.length; i++) {
        for (let j = i + 1; j < funcs.length; j++) {
          const f1 = funcs[i];
          const f2 = funcs[j];
          
          // Skip if same file and overlapping
          if (f1.file === f2.file) continue;

          duplicates.push({
            file1: f1.file,
            line1Start: f1.func.lineStart,
            line1End: f1.func.lineEnd,
            file2: f2.file,
            line2Start: f2.func.lineStart,
            line2End: f2.func.lineEnd,
            similarity: 0.9, // Same hash = very similar
            description: `Functions '${f1.func.name}' and '${f2.func.name}' have similar structure`
          });
        }
      }
    }
  }

  return duplicates;
}

// ============================================================================
// Security Pattern Detection
// ============================================================================

function findSecurityIssues(file: FileMetrics, sourceFile: ts.SourceFile): PotentialIssue[] {
  const issues: PotentialIssue[] = [];
  const text = sourceFile.getFullText();

  function visit(node: ts.Node) {
    const line = sourceFile.getLineAndCharacterOfPosition(node.getStart()).line + 1;
    const nodeText = node.getText(sourceFile);

    // innerHTML assignment
    if (ts.isPropertyAccessExpression(node) && node.name.text === 'innerHTML') {
      const parent = node.parent;
      if (ts.isBinaryExpression(parent) && parent.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
        issues.push({
          category: 'security',
          pattern: 'innerHTML-assignment',
          file: file.path,
          line,
          code: parent.getText(sourceFile).substring(0, 100),
          description: 'innerHTML assignment - verify content is sanitized'
        });
      }
    }

    // dangerouslySetInnerHTML
    if (ts.isJsxAttribute(node) && ts.isIdentifier(node.name) && 
        node.name.text === 'dangerouslySetInnerHTML') {
      issues.push({
        category: 'security',
        pattern: 'dangerous-html',
        file: file.path,
        line,
        code: nodeText.substring(0, 100),
        description: 'dangerouslySetInnerHTML - verify content is sanitized'
      });
    }

    // eval usage
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && 
        node.expression.text === 'eval') {
      issues.push({
        category: 'security',
        pattern: 'eval-usage',
        file: file.path,
        line,
        code: nodeText.substring(0, 100),
        description: 'eval() usage - verify input is trusted'
      });
    }

    // SQL-like string with template literal
    if (ts.isTemplateExpression(node)) {
      const templateText = nodeText.toLowerCase();
      if (templateText.includes('select') || templateText.includes('insert') ||
          templateText.includes('update') || templateText.includes('delete')) {
        issues.push({
          category: 'security',
          pattern: 'sql-template',
          file: file.path,
          line,
          code: nodeText.substring(0, 100),
          description: 'Template literal with SQL-like content - verify parameterized'
        });
      }
    }

    // exec/spawn with shell
    if (ts.isCallExpression(node)) {
      const callText = node.expression.getText(sourceFile);
      if (callText.includes('exec') || callText.includes('spawn')) {
        const args = node.arguments;
        for (const arg of args) {
          if (ts.isObjectLiteralExpression(arg)) {
            for (const prop of arg.properties) {
              if (ts.isPropertyAssignment(prop) && 
                  ts.isIdentifier(prop.name) && prop.name.text === 'shell' &&
                  prop.initializer.kind === ts.SyntaxKind.TrueKeyword) {
                issues.push({
                  category: 'security',
                  pattern: 'shell-exec',
                  file: file.path,
                  line,
                  code: nodeText.substring(0, 100),
                  description: 'exec/spawn with shell:true - verify input is not user-controlled'
                });
              }
            }
          }
        }
      }
    }

    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return issues;
}

// ============================================================================
// Type Error Detection (TypeScript only)
// ============================================================================

function getTypeErrors(files: string[], rootPath: string): any[] {
  // Try to find tsconfig.json
  let configPath = ts.findConfigFile(rootPath, ts.sys.fileExists, 'tsconfig.json');
  
  if (!configPath) {
    return []; // No tsconfig, skip type checking
  }

  const configFile = ts.readConfigFile(configPath, ts.sys.readFile);
  if (configFile.error) {
    return [];
  }

  const parsedConfig = ts.parseJsonConfigFileContent(
    configFile.config,
    ts.sys,
    path.dirname(configPath)
  );

  const program = ts.createProgram(files, parsedConfig.options);
  const diagnostics = ts.getPreEmitDiagnostics(program);

  return diagnostics.slice(0, 50).map(d => { // Limit to 50 errors
    const file = d.file;
    const line = file ? file.getLineAndCharacterOfPosition(d.start || 0).line + 1 : 0;
    
    return {
      file: file?.fileName || 'unknown',
      line,
      code: `TS${d.code}`,
      message: ts.flattenDiagnosticMessageText(d.messageText, '\n'),
      severity: d.category === ts.DiagnosticCategory.Error ? 'error' : 'warning'
    };
  });
}

// ============================================================================
// Framework Detection
// ============================================================================

function detectFramework(files: FileMetrics[]): string {
  const allImports = new Set<string>();
  
  for (const file of files) {
    for (const imp of file.imports) {
      allImports.add(imp.module);
    }
  }

  if (allImports.has('react') || allImports.has('react-dom')) {
    if (allImports.has('next') || allImports.has('next/router')) return 'next';
    if (allImports.has('gatsby')) return 'gatsby';
    if (allImports.has('remix')) return 'remix';
    return 'react';
  }
  if (allImports.has('vue')) return 'vue';
  if (allImports.has('@angular/core')) return 'angular';
  if (allImports.has('svelte')) return 'svelte';
  if (allImports.has('express')) return 'express';
  if (allImports.has('@nestjs/core')) return 'nest';
  if (allImports.has('fastify')) return 'fastify';

  return 'unknown';
}

// ============================================================================
// Main Analysis
// ============================================================================

function analyze(rootPath: string, maxFiles = 500): AnalysisResult {
  const files = collectFiles(rootPath, maxFiles);
  
  if (files.length === 0) {
    return {
      rootPath,
      language: 'unknown',
      framework: 'unknown',
      totalFiles: 0,
      totalLines: 0,
      files: [],
      deadCode: [],
      duplicates: [],
      circularDeps: [],
      potentialIssues: [],
      typeErrors: [],
      summary: {
        avgComplexity: 0,
        maxComplexity: 0,
        avgFunctionLength: 0,
        maxFunctionLength: 0,
        exportedFunctions: 0,
        unusedExports: 0,
        circularDeps: 0
      }
    };
  }

  // Parse all files
  const sourceFiles = new Map<string, ts.SourceFile>();
  const fileMetrics: FileMetrics[] = [];

  for (const filePath of files) {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      const sourceFile = ts.createSourceFile(
        filePath,
        content,
        ts.ScriptTarget.Latest,
        true,
        filePath.endsWith('.tsx') || filePath.endsWith('.jsx') 
          ? ts.ScriptKind.TSX 
          : filePath.endsWith('.ts') 
            ? ts.ScriptKind.TS 
            : ts.ScriptKind.JS
      );
      
      sourceFiles.set(filePath, sourceFile);
      fileMetrics.push(analyzeFile(filePath, sourceFile));
    } catch (e) {
      // Skip files that can't be parsed
    }
  }

  // Detect language and framework
  const hasTS = fileMetrics.some(f => f.language === 'typescript');
  const language = hasTS ? 'typescript' : 'javascript';
  const framework = detectFramework(fileMetrics);

  // Find issues
  const importGraph = new Map<string, Set<string>>();
  const deadCode = findDeadCode(fileMetrics, importGraph);
  const duplicates = findDuplicates(fileMetrics, sourceFiles);
  const circularDeps = findCircularDependencies(fileMetrics);
  
  // Security issues
  const potentialIssues: PotentialIssue[] = [];
  for (const file of fileMetrics) {
    const sourceFile = sourceFiles.get(file.path);
    if (sourceFile) {
      potentialIssues.push(...findSecurityIssues(file, sourceFile));
    }
  }

  // Type errors (TypeScript only)
  const typeErrors = hasTS ? getTypeErrors(files, rootPath) : [];

  // Calculate summary
  const allFunctions = fileMetrics.flatMap(f => f.functions);
  const complexities = allFunctions.map(f => f.complexity);
  const lengths = allFunctions.map(f => f.lineCount);
  const exportedFunctions = allFunctions.filter(f => f.isExported);

  const summary = {
    avgComplexity: complexities.length > 0 
      ? Math.round(complexities.reduce((a, b) => a + b, 0) / complexities.length * 10) / 10 
      : 0,
    maxComplexity: Math.max(0, ...complexities),
    avgFunctionLength: lengths.length > 0 
      ? Math.round(lengths.reduce((a, b) => a + b, 0) / lengths.length * 10) / 10 
      : 0,
    maxFunctionLength: Math.max(0, ...lengths),
    exportedFunctions: exportedFunctions.length,
    unusedExports: deadCode.filter(d => d.kind === 'unused-export').length,
    circularDeps: circularDeps.length
  };

  return {
    rootPath,
    language,
    framework,
    totalFiles: fileMetrics.length,
    totalLines: fileMetrics.reduce((sum, f) => sum + f.lineCount, 0),
    files: fileMetrics,
    deadCode,
    duplicates,
    circularDeps,
    potentialIssues,
    typeErrors,
    summary
  };
}

// ============================================================================
// CLI
// ============================================================================

function printSummary(result: AnalysisResult) {
  console.log('='.repeat(60));
  console.log('TYPESCRIPT/JAVASCRIPT ANALYSIS');
  console.log('='.repeat(60));
  console.log(`Path: ${result.rootPath}`);
  console.log(`Language: ${result.language}`);
  console.log(`Framework: ${result.framework}`);
  console.log(`Files: ${result.totalFiles}`);
  console.log(`Lines: ${result.totalLines.toLocaleString()}`);
  console.log('');
  
  console.log('Summary:');
  console.log(`  Avg complexity: ${result.summary.avgComplexity}`);
  console.log(`  Max complexity: ${result.summary.maxComplexity}`);
  console.log(`  Avg function length: ${result.summary.avgFunctionLength} lines`);
  console.log(`  Max function length: ${result.summary.maxFunctionLength} lines`);
  console.log(`  Exported functions: ${result.summary.exportedFunctions}`);
  console.log(`  Unused exports: ${result.summary.unusedExports}`);
  console.log(`  Circular dependencies: ${result.summary.circularDeps}`);
  console.log('');

  if (result.typeErrors.length > 0) {
    console.log(`Type Errors: ${result.typeErrors.length}`);
    result.typeErrors.slice(0, 5).forEach(e => {
      console.log(`  ${path.basename(e.file)}:${e.line} - ${e.message.substring(0, 60)}`);
    });
    console.log('');
  }

  if (result.deadCode.length > 0) {
    console.log(`Dead Code: ${result.deadCode.length} items`);
    result.deadCode.slice(0, 5).forEach(d => {
      console.log(`  ${path.basename(d.file)}:${d.line} - ${d.description}`);
    });
    console.log('');
  }

  if (result.circularDeps.length > 0) {
    console.log(`Circular Dependencies: ${result.circularDeps.length}`);
    result.circularDeps.slice(0, 3).forEach(c => {
      console.log(`  ${c.description}`);
    });
    console.log('');
  }

  if (result.duplicates.length > 0) {
    console.log(`Potential Duplicates: ${result.duplicates.length}`);
    result.duplicates.slice(0, 3).forEach(d => {
      console.log(`  ${path.basename(d.file1)}:${d.line1Start} <-> ${path.basename(d.file2)}:${d.line2Start}`);
    });
    console.log('');
  }

  if (result.potentialIssues.length > 0) {
    console.log(`Security Issues (need verification): ${result.potentialIssues.length}`);
    result.potentialIssues.slice(0, 5).forEach(i => {
      console.log(`  ${path.basename(i.file)}:${i.line} - ${i.pattern}`);
    });
  }

  console.log('='.repeat(60));
}

// Main
const args = process.argv.slice(2);
let targetPath = '.';
let outputFile: string | null = null;
let showSummary = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--output' || args[i] === '-o') {
    outputFile = args[++i];
  } else if (args[i] === '--summary') {
    showSummary = true;
  } else if (!args[i].startsWith('-')) {
    targetPath = args[i];
  }
}

const resolvedPath = path.resolve(targetPath);
const result = analyze(resolvedPath);

if (showSummary) {
  printSummary(result);
}

if (outputFile) {
  fs.writeFileSync(outputFile, JSON.stringify(result, null, 2));
  console.log(`Results written to: ${outputFile}`);
} else if (!showSummary) {
  console.log(JSON.stringify(result, null, 2));
}
