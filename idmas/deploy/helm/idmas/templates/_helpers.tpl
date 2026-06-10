{{- define "idmas.labels" -}}
app.kubernetes.io/name: idmas
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "idmas.envFrom" -}}
- configMapRef:
    name: {{ .Release.Name }}-config
- secretRef:
    name: {{ .Release.Name }}-secrets
{{- end -}}
