package com.omni.smart.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class AqiData {
    @SerializedName("list")
    private List<AqiItem> list;

    public static class AqiItem {
        @SerializedName("main")
        public Main main;
        
        @SerializedName("components")
        public Components components;
    }

    public static class Main {
        @SerializedName("aqi")
        public int aqi;
    }

    public static class Components {
        @SerializedName("pm10")
        public double pm10;
        @SerializedName("pm2_5")
        public double pm25;
    }

    public int getAqi() {
        return (list != null && !list.isEmpty()) ? list.get(0).main.aqi : 0;
    }
    
    public double getPm10() {
        return (list != null && !list.isEmpty()) ? list.get(0).components.pm10 : 0;
    }

    public double getPm25() {
        return (list != null && !list.isEmpty()) ? list.get(0).components.pm25 : 0;
    }
}
