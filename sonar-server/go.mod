module sonar-server

go 1.13

require (
	gopkg.in/yaml.v2 v2.4.0
	sonar.client v0.0.0
)

replace sonar.client => ../sonar.client
