package com.omni.smart.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class RecommendRequest {
    @SerializedName("context")
    private UserContext context;
    
    @SerializedName("exclude_ids")
    private List<String> excludedIds;

    public RecommendRequest() {}

    public RecommendRequest(UserContext context, List<String> excludedIds) {
        this.context = context;
        this.excludedIds = excludedIds;
    }

    public UserContext getContext() { return context; }
    public void setContext(UserContext context) { this.context = context; }

    public List<String> getExcludedIds() { return excludedIds; }
    public void setExcludedIds(List<String> excludedIds) { this.excludedIds = excludedIds; }
}
