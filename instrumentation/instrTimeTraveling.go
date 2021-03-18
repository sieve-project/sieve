package main

import (
	"go/token"
	"io/ioutil"
	"os"

	"github.com/dave/dst"

	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/goast"
)

func instrumentReflectorGo(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "cache", goast.New())
	f, err := dec.Parse(code)
	check(err)

	_, funcDecl := findFuncDecl(f, "LastSyncResourceVersion")
	if funcDecl == nil {
		panic("instrumentReflectorGo error")
	}
	index, _ := findFuncDecl(f, "setExpectedType")
	if index == -1 {
		panic("instrumentReflectorGo error")
	}

	instrumentation := dst.Clone(funcDecl).(*dst.FuncDecl)
	instrumentation.Name = &dst.Ident{Name: "GetExpectedTypeName"}
	instrumentation.Body.List = []dst.Stmt{&dst.ReturnStmt{Results: []dst.Expr{
		&dst.Ident{Name: "r.expectedTypeName"},
	}}}
	instrumentation.Decs.Start.Replace("//soanr")
	index = index + 1
	f.Decls = append(f.Decls[:index+1], f.Decls[index:]...)
	f.Decls[index] = instrumentation

	writeInstrumentedFile("cache", ofilepath, f)
}

func instrumentCacherGo(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "cacher", goast.New())
	f, err := dec.Parse(code)
	check(err)

	_, funcDecl := findFuncDecl(f, "NewCacherFromConfig")
	if funcDecl == nil {
		panic("instrumentCacherGo error")
	}

	index := -1
	for i, stmt := range funcDecl.Body.List {
		if assignStmt, ok := stmt.(*dst.AssignStmt); ok {
			if ident, ok := assignStmt.Lhs[0].(*dst.Ident); ok {
				if ident.Name == "reflector" {
					index = i
				}
			}
		}
	}
	if index == -1 {
		panic("instrumentCacherGo error")
	}

	// log out type name for checking status
	instrumentation := &dst.ExprStmt{
		X: &dst.CallExpr{
			Fun: &dst.Ident{Name: "Infof", Path: "k8s.io/klog"},
			Args: []dst.Expr{
				&dst.Ident{
					Name: "\"[sonar][type] %s\"",
				},
				&dst.CallExpr{
					Fun: &dst.SelectorExpr{
						X:   &dst.Ident{Name: "reflector"},
						Sel: &dst.Ident{Name: "GetExpectedTypeName"},
					},
					Args: []dst.Expr{},
				},
			},
		},
	}
	instrumentation.Decs.Start.Append("//sonar")
	index = index + 1
	funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
	funcDecl.Body.List[index] = instrumentation

	if os.Args[1] == "time-travel" {
		instrumentation = &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun: &dst.SelectorExpr{
					X:   &dst.Ident{Name: "watchCache"},
					Sel: &dst.Ident{Name: "SetExpectedTypeName"},
				},
				Args: []dst.Expr{
					&dst.CallExpr{
						Fun: &dst.SelectorExpr{
							X:   &dst.Ident{Name: "reflector"},
							Sel: &dst.Ident{Name: "GetExpectedTypeName"},
						},
						Args: []dst.Expr{},
					},
				},
			},
		}
		instrumentation.Decs.Start.Append("//sonar")
		index = index + 1
		funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
		funcDecl.Body.List[index] = instrumentation
	}

	writeInstrumentedFile("cacher", ofilepath, f)
}

func instrumentWatchCacheGo(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "cacher", goast.New())
	f, err := dec.Parse(code)
	check(err)

	index, funcDecl := findFuncDecl(f, "processEvent")
	if funcDecl == nil {
		panic("instrumentWatchCacheGo error")
	}

	instrumentation := &dst.FuncDecl{
		Recv: &dst.FieldList{
			Opening: true,
			List: []*dst.Field{
				&dst.Field{
					Names: []*dst.Ident{&dst.Ident{Name: "w"}},
					Type:  &dst.StarExpr{X: &dst.Ident{Name: "watchCache"}},
					Tag:   nil,
				},
			},
			Closing: true,
		},
		Name: &dst.Ident{Name: "SetExpectedTypeName"},
		Type: &dst.FuncType{
			Func: true,
			Params: &dst.FieldList{
				Opening: true,
				List: []*dst.Field{
					&dst.Field{
						Names: []*dst.Ident{&dst.Ident{Name: "expectedTypeName"}},
						Type:  &dst.Ident{Name: "string"},
						Tag:   nil,
					},
				},
				Closing: true,
			},
			Results: &dst.FieldList{
				Opening: false,
				List:    []*dst.Field{},
				Closing: false,
			},
		},
		Body: &dst.BlockStmt{
			List: []dst.Stmt{
				&dst.AssignStmt{
					Lhs: []dst.Expr{
						&dst.SelectorExpr{
							X:   &dst.Ident{Name: "w"},
							Sel: &dst.Ident{Name: "expectedTypeName"},
						},
					},
					Tok: token.ASSIGN,
					Rhs: []dst.Expr{
						&dst.Ident{Name: "expectedTypeName"},
					},
				},
			},
			RbraceHasNoPos: false,
		},
	}
	instrumentation.Decs.Start.Append("//sonar")
	f.Decls = append(f.Decls[:index+1], f.Decls[index:]...)
	f.Decls[index] = instrumentation

	index = 0
	funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
	instrumentationInEventProcesss := &dst.ExprStmt{
		X: &dst.CallExpr{
			Fun:  &dst.Ident{Name: "NotifyBeforeProcessEvent", Path: "sonar.client"},
			Args: []dst.Expr{&dst.Ident{Name: "string(event.Type)"}, &dst.Ident{Name: "w.expectedTypeName"}},
		},
	}
	instrumentationInEventProcesss.Decs.End.Append("//sonar: NotifyBeforeProcessEvent")
	funcDecl.Body.List[index] = instrumentationInEventProcesss

	_, _, typeSpec := findTypeDecl(f, "watchCache")
	if typeSpec == nil {
		panic("instrumentWatchCacheGo error")
	}
	structType := typeSpec.Type.(*dst.StructType)
	instrumentationInWatchCacheStructure := &dst.Field{
		Names: []*dst.Ident{&dst.Ident{Name: "expectedTypeName"}},
		Type:  &dst.Ident{Name: "string"},
	}
	instrumentationInWatchCacheStructure.Decs.Start.Append("//sonar")
	structType.Fields.List = append(structType.Fields.List, instrumentationInWatchCacheStructure)

	writeInstrumentedFile("cacher", ofilepath, f)
}
