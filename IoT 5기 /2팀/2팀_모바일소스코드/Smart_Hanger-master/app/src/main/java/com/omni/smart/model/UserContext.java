package com.omni.smart.model;

import com.google.gson.annotations.SerializedName;
import java.util.ArrayList;
import java.util.List;

public class UserContext {
    @SerializedName("latitude")
    private double latitude;
    
    @SerializedName("longitude")
    private double longitude;
    
    @SerializedName("weather")
    private String weather = "Unknown";
    
    @SerializedName("aqi")
    private int aqi = 0;
    
    @SerializedName("schedule_status")
    private String scheduleStatus = "free";

    @SerializedName("schedule")
    private List<ScheduleItem> schedule = new ArrayList<>();

    public static class ScheduleItem {
        @SerializedName("time") public String time;
        @SerializedName("event") public String event;
        public ScheduleItem(String time, String event) { this.time = time; this.event = event; }
    }

    public UserContext() {}

    public double getLatitude() { return latitude; }
    public void setLatitude(double latitude) { this.latitude = latitude; }

    public double getLongitude() { return longitude; }
    public void setLongitude(double longitude) { this.longitude = longitude; }

    public String getWeather() { return weather; }
    public void setWeather(String weather) { this.weather = weather; }

    public int getAqi() { return aqi; }
    public void setAqi(int aqi) { this.aqi = aqi; }

    public String getScheduleStatus() { return scheduleStatus; }
    public void setScheduleStatus(String scheduleStatus) { this.scheduleStatus = scheduleStatus; }

    public List<ScheduleItem> getSchedule() { return schedule; }
    public void setSchedule(List<ScheduleItem> schedule) { this.schedule = schedule; }
}
