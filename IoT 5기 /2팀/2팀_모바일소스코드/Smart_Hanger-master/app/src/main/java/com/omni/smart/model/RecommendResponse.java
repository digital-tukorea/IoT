package com.omni.smart.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class RecommendResponse {
    @SerializedName("recommendations")
    private List<Clothing> recommendations;

    public RecommendResponse() {}

    public List<Clothing> getRecommendations() { return recommendations; }
    public void setRecommendations(List<Clothing> recommendations) { this.recommendations = recommendations; }
}
