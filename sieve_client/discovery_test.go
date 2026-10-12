package sieve

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"reflect"
	"runtime"
	"sync/atomic"
	"testing"

	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
)

func TestResolveResourceType(t *testing.T) {
	frame := runtime.FuncForPC(reflect.ValueOf(TestResolveResourceType).Pointer()).Name()
	plan, _ := json.Marshal(map[string]interface{}{"annotatedReconcileStackFrame": []string{frame}, "actions": []interface{}{}})
	previous, present := os.LookupEnv("sieveTestPlan")
	if err := os.Setenv("sieveTestPlan", string(plan)); err != nil {
		t.Fatal(err)
	}
	defer func() {
		if present {
			os.Setenv("sieveTestPlan", previous)
		} else {
			os.Unsetenv("sieveTestPlan")
		}
		config = nil
		delete(annotatedReconcileFunctions, frame)
	}()

	var requests int32
	server := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&requests, 1)
		if r.URL.RawQuery != "" || r.Header.Get("Accept") != "application/json" {
			t.Errorf("unexpected discovery request: %s, Accept=%q", r.URL, r.Header.Get("Accept"))
		}
		var body string
		switch r.URL.Path {
		case "/prefix/apis/outbox.example/v1":
			body = `{"resources":[{"name":"kubeoutboxes","singularName":"kubeoutbox","kind":"KubeOutbox"},{"name":"kubeoutboxes/status","kind":"Status"},{"name":"people","singularName":"human","kind":"Person"}]}`
		case "/prefix/apis/other.example/v1":
			body = `{"resources":[{"name":"kubeoutboxes","kind":"OtherKind"}]}`
		case "/prefix/apis/outbox.example/v2":
			body = `{"resources":[{"name":"kubeoutboxes","kind":"VersionTwo"}]}`
		case "/prefix/api/v1":
			body = `{"resources":[{"name":"namespaces","kind":"Namespace"}]}`
		default:
			http.Error(w, "unavailable", http.StatusForbidden)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(body))
	}))
	defer server.Close()
	u, _ := url.Parse(server.URL + "/prefix/apis/outbox.example/v1/namespaces/default/kubeoutboxes/example/status?timeout=1s")
	for _, mode := range []string{TEST, LEARN} {
		for _, c := range []struct{ path, plural, kind string }{
			{"/prefix/apis/outbox.example/v1", "kubeoutboxes", "KubeOutbox"},
			{"/prefix/apis/outbox.example/v1", "people", "Person"},
			{"/prefix/apis/other.example/v1", "kubeoutboxes", "OtherKind"},
			{"/prefix/apis/outbox.example/v2", "kubeoutboxes", "VersionTwo"},
			{"/prefix/api/v1", "namespaces", "Namespace"},
		} {
			kind := ResolveResourceType(context.Background(), server.Client(), u, c.path, c.plural, mode)
			obj := &unstructured.Unstructured{}
			obj.SetKind(c.kind)
			obj.SetName("example")
			want := generateResourceKey(getResourceTypeFromObj(obj), "default", "example")
			for _, verb := range []string{HTTP_GET, HTTP_POST, HTTP_PUT, HTTP_PATCH, HTTP_DELETE} {
				if got := generateResourceKeyFromRestCall(verb, kind, "default", "example", obj); got != want {
					t.Errorf("%s %s %s: key %q, want %q", mode, verb, c.plural, got, want)
				}
			}
		}
	}
	if got := atomic.LoadInt32(&requests); got != 4 {
		t.Fatalf("successful discovery was not cached: %d requests, want 4", got)
	}

	var available int32
	other := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch atomic.LoadInt32(&available) {
		case 0:
			w.WriteHeader(http.StatusForbidden)
		case 1:
			w.Write([]byte(`{"resources":[]}`))
		default:
			w.Write([]byte(`{"resources":[{"name":"kubeoutboxes","kind":"NewKind"}]}`))
		}
	}))
	defer other.Close()
	u, _ = url.Parse(other.URL)
	for i, want := range []string{"", "", "newkind"} {
		atomic.StoreInt32(&available, int32(i))
		got := ResolveResourceType(context.Background(), other.Client(), u, "/prefix/apis/outbox.example/v1", "kubeoutboxes", TEST)
		if got != want {
			t.Fatalf("discovery attempt %d: got %q, want %q", i, got, want)
		}
	}
}
