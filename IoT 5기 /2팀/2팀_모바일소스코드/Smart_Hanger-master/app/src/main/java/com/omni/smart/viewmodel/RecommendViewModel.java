package com.omni.smart.viewmodel;

import android.app.Application;

import androidx.annotation.NonNull;
import androidx.lifecycle.AndroidViewModel;
import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;

import com.omni.smart.model.Clothing;
import com.omni.smart.model.RecommendRequest;
import com.omni.smart.model.UserContext;
import com.omni.smart.repository.ClothingRepository;

import java.util.ArrayList;
import java.util.List;

public class RecommendViewModel extends AndroidViewModel {
    private final ClothingRepository repository;
    private final MutableLiveData<List<Clothing>> recommendations = new MutableLiveData<>();
    private final MutableLiveData<Boolean> isLoading = new MutableLiveData<>(false);
    private final MutableLiveData<String> statusMessage = new MutableLiveData<>();
    private final List<String> excludedIds = new ArrayList<>();

    public RecommendViewModel(@NonNull Application application) {
        super(application);
        repository = new ClothingRepository();
    }

    public void fetchRecommendations(UserContext context, boolean clearExclusions) {
        // Clear previous exclusions to only send the IDs currently visible on screen
        excludedIds.clear();
        
        if (!clearExclusions) {
            List<Clothing> current = recommendations.getValue();
            if (current != null) {
                for (Clothing c : current) {
                    if (c != null && c.getId() != null) {
                        excludedIds.add(c.getId());
                    }
                }
            }
        }

        isLoading.setValue(true);
        
        repository.submitContext(context, success -> {
            RecommendRequest request = new RecommendRequest(context, new ArrayList<>(excludedIds));
            repository.getRecommendation(request, response -> {
                isLoading.setValue(false);
                if (response != null && response.getRecommendations() != null) {
                    if (response.getRecommendations().isEmpty()) {
                        statusMessage.setValue("No more new recommendations available.");
                    }
                    recommendations.setValue(response.getRecommendations());
                } else {
                    statusMessage.setValue("Failed to get recommendations from server.");
                }
            });
        });
    }

    public LiveData<List<Clothing>> getRecommendations() {
        return recommendations;
    }

    public LiveData<Boolean> getIsLoading() {
        return isLoading;

    }

    public LiveData<String> getStatusMessage() {
        return statusMessage;
    }
}
