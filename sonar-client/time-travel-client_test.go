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
	namespace := tokens[len(tokens)-2]
	name := tokens[len(tokens)-1]
	assert.Equal(t, "service", resourceType)
	assert.Equal(t, "default", namespace)
	assert.Equal(t, "mongodb-cluster-cfg", name)
}
