package main

type TriggerNotification interface {
	printNotification()
}

type TimeoutNotification struct {
	conditionName string
}

func (tn *TimeoutNotification) printNotification() {

}

type ObjectCreateNotification struct {
	resourceKey  string
	observedWhen string
	observedBy   string
}

func (ocn *ObjectCreateNotification) printNotification() {

}

type ObjectDeleteNotification struct {
	resourceKey  string
	observedWhen string
	observedBy   string
}

func (odn *ObjectDeleteNotification) printNotification() {

}
