package sonar

type Response struct {
	Message string
	Ok      bool
	Wait    int
}

type EchoRequest struct {
	Text string
}

type NotifyBeforeMakeQRequest struct {
	QueueID        string
	ControllerName string
}

type NotifyBeforeQAddRequest struct {
	QueueID string
}

type NotifyBeforeReconcileRequest struct {
	ControllerName string
}

type NotifyBeforeProcessEventRequest struct {
	EventType    string
	ResourceType string
	Hostname     string
}
