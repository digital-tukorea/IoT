package com.omni.smart.model;

import com.google.gson.annotations.SerializedName;

public class Aqi {
    @SerializedName("aqi")
    private int aqi;
    
    @SerializedName("pm10")
    private double pm10;
    
    @SerializedName("pm25")
    private double pm25;

    public Aqi() {}

    public int getAqi() { return aqi; }
    public void setAqi(int aqi) { this.aqi = aqi; }

    public double getPm10() { return pm10; }
    public void setPm10(double pm10) { this.pm10 = pm10; }

    public double getPm25() { return pm25; }
    public void setPm25(double pm25) { this.pm25 = pm25; }
}
