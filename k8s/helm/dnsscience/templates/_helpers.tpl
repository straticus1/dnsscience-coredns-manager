{{/*
Expand the name of the chart.
*/}}
{{- define "dnsscience.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "dnsscience.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "dnsscience.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "dnsscience.labels" -}}
helm.sh/chart: {{ include "dnsscience.chart" . }}
{{ include "dnsscience.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "dnsscience.selectorLabels" -}}
app.kubernetes.io/name: {{ include "dnsscience.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use for the operator
*/}}
{{- define "dnsscience.operator.serviceAccountName" -}}
{{- if .Values.operator.serviceAccount.create }}
{{- default (printf "%s-operator" (include "dnsscience.fullname" .)) .Values.operator.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.operator.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
API component labels
*/}}
{{- define "dnsscience.api.labels" -}}
{{ include "dnsscience.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
API selector labels
*/}}
{{- define "dnsscience.api.selectorLabels" -}}
{{ include "dnsscience.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Admin component labels
*/}}
{{- define "dnsscience.admin.labels" -}}
{{ include "dnsscience.labels" . }}
app.kubernetes.io/component: admin
{{- end }}

{{/*
Admin selector labels
*/}}
{{- define "dnsscience.admin.selectorLabels" -}}
{{ include "dnsscience.selectorLabels" . }}
app.kubernetes.io/component: admin
{{- end }}

{{/*
Operator component labels
*/}}
{{- define "dnsscience.operator.labels" -}}
{{ include "dnsscience.labels" . }}
app.kubernetes.io/component: operator
{{- end }}

{{/*
Operator selector labels
*/}}
{{- define "dnsscience.operator.selectorLabels" -}}
{{ include "dnsscience.selectorLabels" . }}
app.kubernetes.io/component: operator
{{- end }}
