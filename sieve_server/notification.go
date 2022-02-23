package main

type TriggerNotification interface {
	getBlockingCh() chan string
}

type TimeoutNotification struct {
	conditionName string
}

func (tn *TimeoutNotification) getBlockingCh() chan string {
	return nil
}

type ObjectCreateNotification struct {
	resourceKey  string
	observedWhen string
	observedBy   string
	blockingCh   chan string
}

func (ocn *ObjectCreateNotification) getBlockingCh() chan string {
	return ocn.blockingCh
}

type ObjectDeleteNotification struct {
	resourceKey  string
	observedWhen string
	observedBy   string
	blockingCh   chan string
}

func (odn *ObjectDeleteNotification) getBlockingCh() chan string {
	return odn.blockingCh
}
