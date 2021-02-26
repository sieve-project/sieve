package sonar

type Response struct {
	Message string
	Ok      bool
	Wait    int
}

type EchoRequest struct {
	Text string
}

type RegisterQueueRequest struct {
	QueueID        string
	ControllerName string
}

type PushIntoQueueRequest struct {
	QueueID string
}

type WaitBeforeReconcileRequest struct {
	ControllerName string
}

type WaitBeforeProcessEventRequest struct {
	EventType    string
	ResourceType string
	Hostname     string
}
