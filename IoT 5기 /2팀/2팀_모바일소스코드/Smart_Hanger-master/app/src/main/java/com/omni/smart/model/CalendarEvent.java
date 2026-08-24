package com.omni.smart.model;

public class CalendarEvent {
    private long id;
    private String title;
    private long startTime;
    private long endTime;
    private String location;
    private boolean allDay;

    // 기존 코드 호환용 (그대로 둠)
    public CalendarEvent(String title, long startTime, long endTime, String location) {
        this(0L, title, startTime, endTime, location, false);
    }

    // 캘린더 화면에서 새로 쓸 생성자
    public CalendarEvent(long id, String title, long startTime, long endTime, String location, boolean allDay) {
        this.id = id;
        this.title = title;
        this.startTime = startTime;
        this.endTime = endTime;
        this.location = location;
        this.allDay = allDay;
    }

    public long getId() { return id; }
    public String getTitle() { return title; }
    public long getStartTime() { return startTime; }
    public long getEndTime() { return endTime; }
    public String getLocation() { return location; }
    public boolean isAllDay() { return allDay; }
}