{% extends 'base.html' %}
{% block title %}Subscriber Dashboard{% endblock %}

{% block content %}
<div class="hero">
  <h1>Subscriber dashboard</h1>
  <p>Review who signed up for release and restock notifications.</p>

  {% if subscribers %}
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Phone</th>
          <th>Channel</th>
          <th>Interest</th>
          <th>Joined</th>
        </tr>
      </thead>
      <tbody>
        {% for s in subscribers %}
          <tr>
            <td>{{ s.name or '—' }}</td>
            <td>{{ s.email }}</td>
            <td>{{ s.phone or '—' }}</td>
            <td>{{ s.preferred_channel }}</td>
            <td>{{ s.product_interest or '—' }}</td>
            <td>{{ s.created_at }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>No subscribers yet.</p>
  {% endif %}
</div>
{% endblock %}
