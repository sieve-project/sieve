package sonar

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestToken(t *testing.T) {
	key := "/services/endpoints/default/mongodb-cluster-cfg"
	tokens := strings.Split(key, "/")
	if len(tokens) < 4 {
		return
	}
	resourceType := pluralToSingle(tokens[len(tokens)-3])
	prev := tokens[len(tokens)-4]
	cur := tokens[len(tokens)-3]
	if prev == "services" && cur == "endpoints" {
		resourceType = "endpoints"
	}
	if prev == "services" && cur == "specs" {
		resourceType = "service"
	}

	namespace := tokens[len(tokens)-2]
	name := tokens[len(tokens)-1]
	assert.Equal(t, "endpoints", resourceType)
	assert.Equal(t, "default", namespace)
	assert.Equal(t, "mongodb-cluster-cfg", name)
}
