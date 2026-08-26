{% for issue in issues -%}
{{ issue.details.file }}:{{ issue.details.line }} {{ issue.details.source }}{% if issue.details.content %}  {{ issue.details.content }}{% endif %}
{% if issue.details.message %}  {{ issue.details.message }}
{% endif %}
{%- endfor %}
