package com.omni.smart.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class WeatherData {
    @SerializedName("main")
    private Main main;

    @SerializedName("weather")
    private List<WeatherDescription> weather;

    @SerializedName("wind")
    private Wind wind;

    @SerializedName("name")
    private String cityName;

    public static class Main {
        @SerializedName("temp")
        public double temp;
        @SerializedName("humidity")
        public int humidity;
        @SerializedName("feels_like")
        public double feelsLike;
    }

    public static class Wind {
        @SerializedName("speed")
        public double speed;
    }

    public static class WeatherDescription {
        @SerializedName("main")
        public String main;
        @SerializedName("description")
        public String description;
        @SerializedName("icon")
        public String icon;
    }

    public double getTemp() { return main != null ? main.temp : 0; }
    public int getHumidity() { return main != null ? main.humidity : 0; }
    public double getFeelsLike() { return main != null ? main.feelsLike : 0; }
    public double getWindSpeed() { return wind != null ? wind.speed : 0; }
    public String getCondition() { return (weather != null && !weather.isEmpty()) ? weather.get(0).main : "Unknown"; }
    public String getIcon() { return (weather != null && !weather.isEmpty()) ? weather.get(0).icon : ""; }
    public String getCityName() { return cityName; }
}