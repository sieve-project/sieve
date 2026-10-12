package sieve

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

type discoveryKey struct {
	client   *http.Client
	url      string
	resource string
}

var discoveredKinds sync.Map

// ResolveResourceType maps a REST resource to the lowercase Kind used by cache
// and informer hooks. Use the operator's transport rather than client-go here:
// instrumented client-go itself imports sieve.client.
func ResolveResourceType(ctx context.Context, client *http.Client, requestURL *url.URL, apiPath, resource, mode string) string {
	if resource == "" {
		return ""
	}
	if err := loadSieveConfigFromEnv(mode == TEST); err != nil {
		return ""
	}
	if getMatchedReconcileStackFrame() == UNKNOWN_RECONCILE_FUN {
		return ""
	}
	kind, err := discoverResourceType(ctx, client, requestURL, apiPath, resource)
	if err != nil {
		log.Printf("Sieve resource discovery failed for %s/%s: %v", apiPath, resource, err)
		return ""
	}
	return kind
}

func discoverResourceType(ctx context.Context, client *http.Client, requestURL *url.URL, apiPath, resource string) (string, error) {
	u := *requestURL
	u.Path, u.RawPath, u.RawQuery, u.Fragment = apiPath, "", "", ""
	if client == nil {
		client = http.DefaultClient
	}
	key := discoveryKey{client: client, url: u.String(), resource: resource}
	if kind, ok := discoveredKinds.Load(key); ok {
		return kind.(string), nil
	}
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("Accept", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("discovery returned HTTP %d", resp.StatusCode)
	}
	var resources metav1.APIResourceList
	if err := json.NewDecoder(resp.Body).Decode(&resources); err != nil {
		return "", err
	}
	for _, r := range resources.APIResources {
		if r.Kind != "" && !strings.Contains(r.Name, "/") {
			discoveredKinds.Store(discoveryKey{client: client, url: u.String(), resource: r.Name}, strings.ToLower(r.Kind))
		}
	}
	if kind, ok := discoveredKinds.Load(key); ok {
		return kind.(string), nil
	}
	// Do not cache missing resources: CRDs may be installed after the operator starts.
	return "", fmt.Errorf("resource is absent from discovery")
}
