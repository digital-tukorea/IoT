package com.omni.smart.fragment;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.lifecycle.ViewModelProvider;
import androidx.recyclerview.widget.GridLayoutManager;

import com.omni.smart.adapter.ClosetAdapter;
import com.omni.smart.databinding.FragmentClosetBinding;
import com.omni.smart.mqtt.MqttHelper;
import com.omni.smart.viewmodel.ClosetViewModel;
import com.omni.smart.viewmodel.HomeViewModel;

public class ClosetFragment extends Fragment {
    private FragmentClosetBinding binding;
    private ClosetViewModel viewModel;
    private ClosetAdapter adapter;
    private HomeViewModel weatherViewModel;

    private MqttHelper mqttHelper;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        binding = FragmentClosetBinding.inflate(inflater, container, false);
        return binding.getRoot();
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        viewModel = new ViewModelProvider(this).get(ClosetViewModel.class);

        mqttHelper = new MqttHelper(requireContext());
        mqttHelper.connect(null);

        setupRecyclerView();
        observeViewModel();

        binding.swipeRefreshCloset.setOnRefreshListener(this::loadClothes);

        weatherViewModel = new ViewModelProvider(requireActivity()).get(HomeViewModel.class);
        weatherViewModel.getCurrentWeather().observe(getViewLifecycleOwner(), weatherData -> {
            if (weatherData != null) {
                String conditionLower = weatherData.getCondition() != null ? weatherData.getCondition().toLowerCase() : "";
                boolean isRainyLook = conditionLower.contains("rain") || conditionLower.contains("drizzle")
                        || conditionLower.contains("thunderstorm") || conditionLower.contains("snow");
                binding.ivClosetBackground.setImageResource(isRainyLook
                        ? com.omni.smart.R.drawable.bg_closet_rain_blur
                        : com.omni.smart.R.drawable.bg_closet_sun_blur);
            }
        });
    }

    private void setupRecyclerView() {
        adapter = new ClosetAdapter(clothing -> {
            if (mqttHelper != null) {
                mqttHelper.publish(clothing.getId(), new org.eclipse.paho.client.mqttv3.IMqttActionListener() {
                    @Override
                    public void onSuccess(org.eclipse.paho.client.mqttv3.IMqttToken asyncActionToken) {
                        requireActivity().runOnUiThread(() ->
                                com.google.android.material.snackbar.Snackbar
                                        .make(binding.getRoot(), clothing.getName() + " 전송 완료", com.google.android.material.snackbar.Snackbar.LENGTH_SHORT)
                                        .show()
                        );
                    }

                    @Override
                    public void onFailure(org.eclipse.paho.client.mqttv3.IMqttToken asyncActionToken, Throwable exception) {
                        requireActivity().runOnUiThread(() ->
                                com.google.android.material.snackbar.Snackbar
                                        .make(binding.getRoot(), "전송 실패 - 연결 확인 필요", com.google.android.material.snackbar.Snackbar.LENGTH_SHORT)
                                        .show()
                        );
                    }
                });
            }
        });
        binding.rvCloset.setLayoutManager(new GridLayoutManager(getContext(), 2));
        binding.rvCloset.setAdapter(adapter);
    }

    private void observeViewModel() {
        loadClothes();
    }

    private void loadClothes() {
        viewModel.getClothes().observe(getViewLifecycleOwner(), clothes -> {
            binding.swipeRefreshCloset.setRefreshing(false);
            if (clothes != null) {
                adapter.setClothingList(clothes);
            } else {
                android.widget.Toast.makeText(getContext(), "Failed to load clothes from server", android.widget.Toast.LENGTH_SHORT).show();
            }
        });
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        if (mqttHelper != null) {
            mqttHelper.disconnect();
        }
        binding = null;
    }
}