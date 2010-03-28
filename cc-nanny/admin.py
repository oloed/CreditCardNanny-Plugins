from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db
from django.utils import simplejson as json
import os
from google.appengine.ext.webapp import template
from google.appengine.api import users

import logging
import reporting
from main import REUpdateEvent
from main import ReportEvent

def stringify(l):
  """docstring for format_list"""
  s = ""
  first = True
  for i in l:
    if first:
      first = False
    else:
      s += ", "
    s += '<a href="/admin/ip_details?ip=%s">%s</a>' % (str(i), str(i))
  return s    


class StaticPageHandler(webapp.RequestHandler):
  def render_page(self, parameters):
    parameters['title'] = self.get_page_title()
    parameters['logout'] = users.create_logout_url("/")
    path = os.path.join(os.path.dirname(__file__), 'templates/' + self.get_page_template_name() + '.html')
    self.response.out.write(template.render(path, parameters))

  def get(self):
    self.render_page({})
    
  def post(self):
    self.get()

class IPDetailsHandler(StaticPageHandler):
  def get_page_title(self):
    return "IP Details for " + self.request.get("ip")

  def get_page_template_name(self):
    return "ip_details"

  def get(self):
    ip = self.request.get("ip")
    params = {"ip_details" : reporting.get_ip_details(ip)}
    self.render_page(params)

class UrlHandler(StaticPageHandler):
  def get_page_title(self):
    return "Offending URLs"

  def get_page_template_name(self):
    return "urls"

  def get(self):
    q = ReportEvent.all()
    m = {}
    for e in q:
      if e.offending_url in m:
        m[e.offending_url].update(e)
      else:
        m[e.offending_url] = OffendingUrl(e)        
    
    dtls = []
    for u in m.items():
      dtls.append(u[1])
    
    dtls.sort()

    self.render_page({"details": dtls, "num_urls": len(dtls)})

class Item(object):
  addresses = []
  count = 0

class OffendingUrl(object):
  def __init__(self, evt):
    self.url = evt.offending_url
    self.count = 1
    self.last_reported = evt.created
    self.first_reported = evt.created
  
  def update(self, evt):
    self.count += 1
    if self.last_reported < evt.created:
      self.last_reported = evt.created
    
    if self.first_reported > evt.created:
      self.first_reported = evt.created

  def __cmp__(self, other):
    return other.count - self.count
    
  

class PluginHandler(StaticPageHandler):
  def get_page_title(self):
    return "Plugin install base"
  
  def get_page_template_name(self):
    return "plugins"
  
  def get(self):
    events = {}
    for ev in REUpdateEvent.all():
      if ev.requestor_ip in events:
        count = events[ev.requestor_ip]
        count += 1
        events[ev.requestor_ip] = count
      else:
        events[ev.requestor_ip] = 1
        
    sorted_events = {}
    for ev in events.items():
      if ev[1] in sorted_events:
        ip_list = sorted_events[ev[1]]
        ip_list.append(ev[0])
      else:
        sorted_events[ev[1]] = [ev[0]]
    
    dtls = []
    for i in sorted_events.items():
      item = Item()
      item.count = i[0]
      item.addresses = i[1]
      dtls.append(item)
    
    self.render_page({"details": dtls, "num_ips": len(events)})
    
    
  
def main():
  application = webapp.WSGIApplication([
      ('/admin', PluginHandler), 
      ('/admin/plugins', PluginHandler), 
      ('/admin/urls', UrlHandler), 
      ('/admin/ip_details', IPDetailsHandler),
      
      ],
                                       debug=False)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
  
