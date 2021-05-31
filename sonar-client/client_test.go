package sonar

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestSB(t *testing.T) {
	client, err := newClient()
	if err != nil {
		t.Fatal(err)
	}
	request := &EchoRequest{
		Text: "Hello",
	}
	response := &Response{}
	client.Call("ObsGapListener.Echo", request, response)
	assert.Equal(t, response.Ok, true)
	assert.Equal(t, response.Message, "echo Hello")
}
