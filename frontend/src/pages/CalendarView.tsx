import React, { useState, useEffect } from "react";
import { Plus, Calendar as CalendarIcon, Clock, MapPin, AlignLeft, RefreshCw } from "lucide-react";
import { calendarUpcoming, calendarCreateEvent } from "../api/client";

export const CalendarView: React.FC = () => {
  const [events, setEvents] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);

  // Form state
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("10:00");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [repeat, setRepeat] = useState("Never");

  useEffect(() => {
    loadUpcoming();
  }, []);

  const loadUpcoming = async () => {
    setIsLoading(true);
    try {
      const data = await calendarUpcoming(10);
      setEvents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !date || !start || !end) return;

    // Build ISO strings assuming local timezone, sending UTC equivalent
    // but the backend accepts timezone field.
    const startDt = new Date(`${date}T${start}:00`).toISOString();
    const endDt = new Date(`${date}T${end}:00`).toISOString();

    let rrule = undefined;
    if (repeat === "Daily") rrule = "FREQ=DAILY";
    else if (repeat === "Weekly") rrule = "FREQ=WEEKLY";
    else if (repeat === "Weekdays") rrule = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR";
    else if (repeat === "Monthly") rrule = "FREQ=MONTHLY";
    else if (repeat === "Yearly") rrule = "FREQ=YEARLY";

    try {
      await calendarCreateEvent({
        title,
        description: description || undefined,
        location: location || undefined,
        start_datetime: startDt,
        end_datetime: endDt,
        all_day: false,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        recurrence_rule: rrule
      });
      setShowForm(false);
      setTitle("");
      setLocation("");
      setDescription("");
      setRepeat("Never");
      loadUpcoming();
    } catch (err) {
      alert("Failed to create event");
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background font-sans overflow-y-auto">
      <header className="px-8 py-6 border-b border-surface-border flex items-center justify-between shrink-0 sticky top-0 bg-background/80 backdrop-blur-md z-10">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800 tracking-tight">Calendar</h1>
          <p className="text-sm text-slate-500 mt-1">Manage your schedule and upcoming events.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-100 p-1 rounded-lg">
            <button className="px-3 py-1.5 text-sm font-medium rounded-md bg-white text-slate-900 shadow-sm">Today</button>
            <button className="px-3 py-1.5 text-sm font-medium rounded-md text-slate-600 hover:text-slate-900">Week</button>
            <button className="px-3 py-1.5 text-sm font-medium rounded-md text-slate-600 hover:text-slate-900">Month</button>
          </div>
          <button 
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            New Event
          </button>
        </div>
      </header>

      <div className="p-8 flex gap-8">
        <div className="flex-1 max-w-3xl">
          {showForm && (
            <div className="mb-8 p-6 bg-white border border-surface-border rounded-xl shadow-sm">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Create Event</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Title</label>
                  <input type="text" value={title} onChange={e=>setTitle(e.target.value)} required className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500" placeholder="Event title" />
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Date</label>
                    <input type="date" value={date} onChange={e=>setDate(e.target.value)} required className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Start</label>
                    <input type="time" value={start} onChange={e=>setStart(e.target.value)} required className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">End</label>
                    <input type="time" value={end} onChange={e=>setEnd(e.target.value)} required className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Location</label>
                    <div className="relative">
                      <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                      <input type="text" value={location} onChange={e=>setLocation(e.target.value)} className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500" placeholder="Add location" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Repeat</label>
                    <div className="relative">
                      <RefreshCw className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                      <select value={repeat} onChange={e=>setRepeat(e.target.value)} className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white">
                        {["Never", "Daily", "Weekly", "Weekdays", "Monthly", "Yearly"].map(r => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                  <div className="relative">
                    <AlignLeft className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                    <textarea value={description} onChange={e=>setDescription(e.target.value)} rows={3} className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 resize-none" placeholder="Add description..." />
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors">
                    Cancel
                  </button>
                  <button type="submit" className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors">
                    Save Event
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">Upcoming Events</h3>
            
            {isLoading ? (
              <div className="text-center py-8 text-slate-400">Loading events...</div>
            ) : events.length === 0 ? (
              <div className="text-center py-12 bg-slate-50 rounded-xl border border-slate-100 border-dashed">
                <CalendarIcon className="w-8 h-8 mx-auto text-slate-300 mb-3" />
                <h3 className="text-slate-700 font-medium">No upcoming events</h3>
                <p className="text-sm text-slate-500 mt-1">Your schedule is clear for the next 30 days.</p>
              </div>
            ) : (
              events.map((ev, i) => {
                const startDate = new Date(ev.start_datetime);
                const endDate = new Date(ev.end_datetime);
                return (
                  <div key={i} className="group p-4 bg-white border border-surface-border rounded-xl shadow-sm hover:border-brand-300 transition-colors flex gap-4 items-start">
                    <div className="w-12 flex flex-col items-center justify-center shrink-0 pt-1">
                      <span className="text-xs font-bold text-brand-600 uppercase tracking-wide">{startDate.toLocaleString('default', { month: 'short' })}</span>
                      <span className="text-xl font-medium text-slate-800">{startDate.getDate()}</span>
                    </div>
                    <div className="w-1 h-12 bg-brand-200 rounded-full mt-1 group-hover:bg-brand-400 transition-colors"></div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-slate-900">{ev.title}</h4>
                      <div className="flex items-center gap-4 mt-1.5 text-sm text-slate-500">
                        <span className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5" />
                          {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        {ev.location && (
                          <span className="flex items-center gap-1.5">
                            <MapPin className="w-3.5 h-3.5" />
                            {ev.location}
                          </span>
                        )}
                        {ev.recurrence_rule && (
                          <span className="flex items-center gap-1.5 text-brand-600 bg-brand-50 px-2 rounded font-medium text-xs">
                            <RefreshCw className="w-3 h-3" />
                            Recurring
                          </span>
                        )}
                      </div>
                      {ev.description && <p className="mt-2 text-sm text-slate-600 line-clamp-2">{ev.description}</p>}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
