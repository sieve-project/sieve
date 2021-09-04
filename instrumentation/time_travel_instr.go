package main

import (
	"github.com/dave/dst"
)

func instrumentWatchCacheGoForTimeTravel(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "cacher")

	_, funcDecl := findFuncDecl(f, "processEvent")
	if funcDecl == nil {
		panic("instrumentWatchCacheGo error")
	}

	instrumentationInProcessEventAfterReconcile := &dst.DeferStmt{
		Call: &dst.CallExpr{
			Fun:  &dst.Ident{Name: "NotifyTimeTravelAfterProcessEvent", Path: "sonar.client"},
			Args: []dst.Expr{&dst.Ident{Name: "string(event.Type)"}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "event.Object"}},
		},
	}
	instrumentationInProcessEventAfterReconcile.Decs.End.Append("//sonar")
	insertStmt(&funcDecl.Body.List, 2, instrumentationInProcessEventAfterReconcile)

	instrumentationInProcessEventBeforeReconcile := &dst.ExprStmt{
		X: &dst.CallExpr{
			Fun:  &dst.Ident{Name: "NotifyTimeTravelBeforeProcessEvent", Path: "sonar.client"},
			Args: []dst.Expr{&dst.Ident{Name: "string(event.Type)"}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "event.Object"}},
		},
	}
	instrumentationInProcessEventBeforeReconcile.Decs.End.Append("//sonar")
	insertStmt(&funcDecl.Body.List, 3, instrumentationInProcessEventBeforeReconcile)

	writeInstrumentedFile(ofilepath, "cacher", f)
}
