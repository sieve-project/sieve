package main

import (
	"bytes"
	"fmt"
	"strings"
	"go/token"
	"os"
	"io/ioutil"
	"github.com/dave/dst/decorator/resolver/goast"

	"github.com/dave/dst"
	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/guess"
)

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func findFuncDecl(f *dst.File, funName string) (int, *dst.FuncDecl) {
	for i, decl := range f.Decls {
		if funcDecl, ok := decl.(*dst.FuncDecl); ok {
			if funcDecl.Name.Name == funName {
				return i, funcDecl
			}
		}
	}
	return -1, nil
}

func findTypeDecl(f *dst.File, typeName string) (int, int, *dst.TypeSpec) {
	for i, decl := range f.Decls {
		if genDecl, ok := decl.(*dst.GenDecl); ok && genDecl.Tok == token.TYPE {
			for j, spec := range genDecl.Specs {
				if typeSpec, ok := spec.(*dst.TypeSpec); ok {
					if typeSpec.Name.Name == typeName {
						return i, j, typeSpec
					}
				}
			}
		}
	}
	return -1, -1, nil
}

func parseSourceFile(ifilepath, pkg string) *dst.File {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), pkg, goast.New())
	f, err := dec.Parse(code)
	check(err)
	return f
}

func insertStmt(list *[]dst.Stmt, index int, instrumentation dst.Stmt) {
	*list = append((*list)[:index+1], (*list)[index:]...)
	(*list)[index] = instrumentation
}

func insertDecl(list *[]dst.Decl, index int, instrumentation dst.Decl) {
	*list = append((*list)[:index+1], (*list)[index:]...)
	(*list)[index] = instrumentation
}

func writeInstrumentedFile(ofilepath, pkg string, f *dst.File) {
	res := decorator.NewRestorerWithImports(pkg, guess.New())
	fres := res.FileRestorer()
	fres.Alias["sonar.client"] = "sonar"
	fres.Alias["k8s.io/klog/v2"] = "klog"

	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = fres.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}

func preprocess(path string) {
	read, err := ioutil.ReadFile(path)
	check(err)
	newContents := strings.Replace(string(read), "\"k8s.io/klog/v2\"", "klog \"k8s.io/klog/v2\"", 1)
	err = ioutil.WriteFile(path, []byte(newContents), 0)
	check(err)
}

func instrumentClientGoForAll(ifilepath, ofilepath, mode string) {
	funName := "Notify" + mode + "SideEffects"
	f := parseSourceFile(ifilepath, "client")

	instrumentSideEffect(f, "Create", funName)
	instrumentSideEffect(f, "Update", funName)
	instrumentSideEffect(f, "Delete", funName)
	instrumentSideEffect(f, "DeleteAllOf", funName)
	instrumentSideEffect(f, "Patch", funName)

	writeInstrumentedFile(ofilepath, "client", f)
}

func instrumentSideEffect(f *dst.File, etype, funName string) {
	_, funcDecl := findFuncDecl(f, etype)
	if funcDecl != nil {
		if returnStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List) - 1].(*dst.ReturnStmt); ok {
			modifiedInstruction := &dst.AssignStmt{
				Lhs: []dst.Expr{&dst.Ident{Name: "err"}},
				Tok: token.DEFINE,
				Rhs: returnStmt.Results,
			}
			modifiedInstruction.Decs.End.Append("//sonar")
			funcDecl.Body.List[len(funcDecl.Body.List) - 1] = modifiedInstruction

			instrumentationExpr := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: funName, Path: "sonar.client"},
					Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", etype)}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
				},
			}
			instrumentationExpr.Decs.End.Append("//sonar")
			funcDecl.Body.List = append(funcDecl.Body.List, instrumentationExpr)

			instrumentationReturn := &dst.ReturnStmt{
				Results: []dst.Expr{&dst.Ident{Name: "err"}},
			}
			instrumentationReturn.Decs.End.Append("//sonar")
			funcDecl.Body.List = append(funcDecl.Body.List, instrumentationReturn)
		} else if switchStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List) - 1].(*dst.TypeSwitchStmt); ok {
			defaultCaseClause, ok := switchStmt.Body.List[len(switchStmt.Body.List) - 1].(*dst.CaseClause)
			if !ok {
				panic(fmt.Errorf("Last stmt in SwitchStmt is not CaseClause"))
			}
			if innerReturnStmt, ok := defaultCaseClause.Body[len(defaultCaseClause.Body) - 1].(*dst.ReturnStmt); ok {
				modifiedInstruction := &dst.AssignStmt{
					Lhs: []dst.Expr{&dst.Ident{Name: "err"}},
					Tok: token.DEFINE,
					Rhs: innerReturnStmt.Results,
				}
				modifiedInstruction.Decs.End.Append("//sonar")
				defaultCaseClause.Body[len(defaultCaseClause.Body) - 1] = modifiedInstruction
	
				instrumentationExpr := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funName, Path: "sonar.client"},
						Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", etype)}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
					},
				}
				instrumentationExpr.Decs.End.Append("//sonar")
				defaultCaseClause.Body = append(defaultCaseClause.Body, instrumentationExpr)
	
				instrumentationReturn := &dst.ReturnStmt{
					Results: []dst.Expr{&dst.Ident{Name: "err"}},
				}
				instrumentationReturn.Decs.End.Append("//sonar")
				defaultCaseClause.Body = append(defaultCaseClause.Body, instrumentationReturn)
			} else {
				panic(fmt.Errorf("Last stmt inside default case of %s is not return", etype))
			}
		} else {
			panic(fmt.Errorf("Last stmt of %s is neither return nor typeswitch", etype))
		}
	} else {
		panic(fmt.Errorf("Cannot find function %s", etype))
	}
}

