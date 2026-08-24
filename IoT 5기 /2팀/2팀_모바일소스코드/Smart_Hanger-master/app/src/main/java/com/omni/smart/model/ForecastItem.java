package com.omni.smart.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class ForecastItem {
    @SerializedName("dt_txt")
    private String dateTime;

    @SerializedName("main")
    private Main main;

    @SerializedName("weather")
    private List<WeatherData.WeatherDescription> weather;

    @SerializedName("pop")
    private double pop; // 강수확률, 0.0 ~ 1.0

    public static class Main {
        @SerializedName("temp")
        public double temp;
    }

    public String getDateTime() { return dateTime; }
    public double getTemp() { return main != null ? main.temp : 0; }
    public String getIcon() { return (weather != null && !weather.isEmpty()) ? weather.get(0).icon : ""; }
    public int getPopPercent() { return (int) Math.round(pop * 100); }
}